// DM3: the Tasks view kept finished agents and background commands as "running".
// Fixture events: the notification burst, a subagent's end, the agent list, and children with no end signal.
import { describe, expect, test } from 'claude-code/testing'

import {
  AGENT_LIST_GRACE_MS, agentState, endAgent, noSignalText, parseTaskNotifications, reconcileAgents, reopenTask, settleTask,
  taskStatusLines, tasksHeadline, type TaskRecord,
} from '../hooks/tasks-logic'

const NOW = Date.UTC(2026, 9, 9, 18, 3)
const rec = (id: string, over: Partial<TaskRecord> = {}): TaskRecord => ({ id, kind: 'bash', label: id, group: 'main', startedAt: NOW - 3600_000, state: 'running', ...over })

// The engine's own notification format, two delivered in one burst.
const note = (id: string, status: string) =>
  `<task-notification>\n<task-id>${id}</task-id>\n<tool-use-id>toolu_x</tool-use-id>\n<output-file>/t/tasks/${id}.output</output-file>\n<status>${status}</status>\n<summary>done</summary>\n</task-notification>`

describe('end signals', () => {
  test('every notification in a burst is read, not only the first', () => {
    const n = parseTaskNotifications(`${note('a1', 'completed')}\n${note('b2', 'failed')}\n${note('c3', 'killed')}`)
    expect(n).toEqual([{ id: 'a1', status: 'completed' }, { id: 'b2', status: 'failed' }, { id: 'c3', status: 'killed' }])
    expect(parseTaskNotifications('no notification here')).toEqual([])
  })

  test('an agent-list word: waiting and idle still run; the end words settle', () => {
    for (const s of ['pending', 'running', 'waiting', 'idle']) expect(agentState(s)).toBe('running')
    expect(agentState('completed')).toBe('completed')
    expect(agentState('failed')).toBe('failed')
    expect(agentState('killed')).toBe('killed')
  })

  test("a subagent's end settles it and marks its still-running children 'no end signal'", () => {
    const list = [
      rec('aM14a', { kind: 'agent' }),
      rec('b1', { parent: 'aM14a' }),
      rec('mon1', { kind: 'monitor', parent: 'aM14a' }),
      rec('b2', { parent: 'aM14a', state: 'completed', endedAt: NOW - 60_000 }),
      rec('bmain', {}),
    ]
    const out = endAgent(list, 'aM14a', 'completed', NOW)
    const by = (id: string) => out.find(t => t.id === id)!
    expect(by('aM14a')).toMatchObject({ state: 'completed', endedAt: NOW })
    expect(by('b1')).toMatchObject({ state: 'no-signal', endedAt: NOW })
    expect(by('mon1').state).toBe('no-signal')
    expect(by('b2')).toMatchObject({ state: 'completed', endedAt: NOW - 60_000 })
    expect(by('bmain').state).toBe('running')
    // A real signal later still wins over "no end signal".
    expect(settleTask(out, 'b1', 'completed', NOW + 5).find(t => t.id === 'b1')).toMatchObject({ state: 'completed', endedAt: NOW + 5 })
  })

  test('the agent list: known ones settle, new ones join, a running one the engine dropped has ended', () => {
    const list = [
      rec('a1', { kind: 'agent' }),
      rec('a2', { kind: 'agent' }),
      rec('a3', { kind: 'agent', startedAt: NOW - 5_000 }),
      rec('kid', { parent: 'a2' }),
    ]
    const agents = [
      { id: 'a1', status: 'completed', description: 'M14a build', type: 'opus-medium' },
      { id: 'a4', status: 'idle', description: 'teammate', type: 'teammate', parentId: 'a1' },
    ]
    const out = reconcileAgents(list, agents, NOW)
    const by = (id: string) => out.find(t => t.id === id)!
    expect(by('a1')).toMatchObject({ state: 'completed', endedAt: NOW })
    expect(by('a4')).toMatchObject({ state: 'running', kind: 'agent', parent: 'a1' })
    // a2 is gone from the list: it ended; the outcome is not reported, and its child has no end signal.
    expect(by('a2')).toMatchObject({ state: 'completed', endedAt: NOW, endNote: 'outcome not reported (gone from the agent list)' })
    expect(by('kid').state).toBe('no-signal')
    // a3 started inside the grace window: not yet judged.
    expect(by('a3').state).toBe('running')
    expect(AGENT_LIST_GRACE_MS).toBeGreaterThan(0)
  })

  test('a finished agent that runs again (SendMessage) is running again', () => {
    const out = reopenTask([rec('a1', { kind: 'agent', state: 'completed', endedAt: NOW - 1000, endNote: 'x' })], 'a1')
    expect(out[0]!.state).toBe('running')
    expect(out[0]!.endedAt).toBe(undefined)
    expect(out[0]!.endNote).toBe(undefined)
  })
})

describe('what the view says', () => {
  test("'no end signal — last output <time>', never 'running'", () => {
    expect(noSignalText(Date.UTC(2026, 9, 9, 15, 42))).toBe('no end signal — last output 15:42 UTC')
    expect(noSignalText(null)).toBe('no end signal — no output seen')
    const t = rec('b1', { parent: 'aM14a', state: 'no-signal', endedAt: NOW - 1000 })
    const lines = taskStatusLines(t, NOW, null, { lastLine: 'ok', idleMs: 2 * 3600_000 + 21 * 60_000, bytes: 10 })
    const text = lines.join('\n')
    expect(text).toMatch(/no end signal — last output 15:42 UTC/)
    expect(text).not.toMatch(/running|estimate/)
  })

  test('the headline counts finished work apart from running work', () => {
    const list = [rec('a'), rec('b', { state: 'no-signal' }), rec('c', { state: 'completed' })]
    expect(tasksHeadline(list, null)).toBe('Tasks: 1 running · 1 no end signal')
  })

  test('an ended agent with no reported outcome says so', () => {
    const t = rec('a2', { kind: 'agent', state: 'completed', endedAt: NOW, endNote: 'outcome not reported (gone from the agent list)' })
    expect(taskStatusLines(t, NOW, null, null).join('\n')).toMatch(/ended {5}18:03 UTC, outcome not reported/)
  })
})
