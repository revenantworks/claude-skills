'use strict'
// Revenantworks dash for VS Code. Reads local files the dash plugin and the status line already
// write (feed.json, the meter file, the budget decision, the switch file) and shows them as status
// bar items and a read-only panel. Never writes a file, never runs a process, never touches the
// network. The panel is static HTML with scripts off.
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
// Loaded inside activate, so plain node can load this file (see the end).
let vscode
const logic = require('./logic')

const REFRESH_MS = 30_000
const SHOW = 'revenantworksDash.showReadout'
const PANEL = 'revenantworksDash.openPanel'

function paths() {
  const home = os.homedir()
  return {
    usage: process.env.CLAUDE_USAGE_WINDOWS || path.join(home, '.claude', 'usage-windows.json'),
    budget: path.join(home, '.dispatch', 'budget-decision.json'),
    switches: path.join(home, '.claude', 'revenantworks', 'switches.json'),
    feed: path.join(home, '.claude', 'revenantworks', 'dash', 'feed.json'),
  }
}

function readText(file) {
  try {
    return fs.readFileSync(file, 'utf8')
  } catch {
    return null
  }
}

function snapshot() {
  const p = paths()
  const now = Date.now()
  return {
    now,
    usage: logic.parseUsage(readText(p.usage), now),
    budget: logic.parseBudget(readText(p.budget), now),
    switches: logic.parseSwitches(readText(p.switches)),
    feed: logic.parseFeed(readText(p.feed), now),
  }
}

function hover(lines) {
  const md = new vscode.MarkdownString(['**Revenantworks dash**', '', ...lines.map(l => `- ${l.replace(/[\\`*_[\]<>]/g, '\\$&')}`), '', '_Click for the panel._'].join('\n'))
  md.isTrusted = false
  return md
}

function activate(context) {
  vscode = require('vscode')
  const pace = vscode.window.createStatusBarItem('revenantworks.dash.pace', vscode.StatusBarAlignment.Left, 100)
  const dash = vscode.window.createStatusBarItem('revenantworks.dash.feed', vscode.StatusBarAlignment.Left, 99)
  const budget = vscode.window.createStatusBarItem('revenantworks.dash.budget', vscode.StatusBarAlignment.Left, 98)
  const kill = vscode.window.createStatusBarItem('revenantworks.dash.kill', vscode.StatusBarAlignment.Left, 97)
  pace.name = 'Revenantworks dash: pace'
  dash.name = 'Revenantworks dash: skills'
  budget.name = 'Revenantworks dash: budget mode'
  kill.name = 'Revenantworks dash: kill switch'
  for (const item of [pace, dash, budget, kill]) {
    item.command = PANEL
    context.subscriptions.push(item)
  }
  let panel = null

  const refresh = () => {
    const s = snapshot()
    const tip = hover(logic.readoutLines(s))

    pace.text = `$(pulse) ${logic.paceText(s.usage)}`
    const look = logic.paceLook(s.usage)
    pace.backgroundColor = look === 'red' ? new vscode.ThemeColor('statusBarItem.errorBackground') : look === 'amber' ? new vscode.ThemeColor('statusBarItem.warningBackground') : undefined
    pace.color = look === 'stale' ? new vscode.ThemeColor('disabledForeground') : undefined
    pace.tooltip = tip
    pace.show()

    const ft = logic.feedText(s.feed)
    if (ft) {
      dash.text = `$(graph) ${ft}`
      dash.tooltip = tip
      dash.show()
    } else dash.hide()

    const bt = logic.budgetText(s.budget)
    if (bt) {
      budget.text = `$(dashboard) ${bt}`
      budget.tooltip = tip
      budget.show()
    } else budget.hide()

    if (s.switches.off) {
      kill.text = '$(circle-slash) MODS OFF'
      kill.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground')
      kill.tooltip = tip
      kill.show()
    } else kill.hide()

    if (panel) panel.webview.html = logic.panelHtml(s)
  }

  context.subscriptions.push(
    vscode.commands.registerCommand(PANEL, () => {
      if (panel) {
        panel.reveal()
        return
      }
      panel = vscode.window.createWebviewPanel('revenantworksDash', 'dash', vscode.ViewColumn.Beside, { enableScripts: false, localResourceRoots: [] })
      panel.onDidDispose(() => { panel = null }, null, context.subscriptions)
      panel.webview.html = logic.panelHtml(snapshot())
    }),
    vscode.commands.registerCommand(SHOW, async () => {
      const lines = logic.readoutLines(snapshot())
      await vscode.window.showQuickPick(lines.map(label => ({ label })), { title: 'Revenantworks dash', placeHolder: 'Read-only readout; Esc closes' })
    }),
  )

  // Refresh on change: watch each file by its folder (writers replace the file by rename).
  for (const file of Object.values(paths())) {
    try {
      const w = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(path.dirname(file)), path.basename(file)))
      w.onDidChange(refresh)
      w.onDidCreate(refresh)
      w.onDidDelete(refresh)
      context.subscriptions.push(w)
    } catch {
      // The 30-second timer still refreshes.
    }
  }
  const timer = setInterval(refresh, REFRESH_MS)
  context.subscriptions.push({ dispose: () => clearInterval(timer) })
  refresh()
}

function deactivate() {}

module.exports = { activate, deactivate }

// `node --test mods/vscode` runs this folder's package main as a test file; hand it the tests.
if (require.main === module) require('./logic.test.js')
