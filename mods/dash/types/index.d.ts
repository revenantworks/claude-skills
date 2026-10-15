// dash's $.state contract. Two values: the pane's revision, bumped by every press in the pane
// and by every typed /dash view command, and the band's (below).
// The pane reads it while drawing, so a press redraws it at once through the state write
// rather than through an invalidate the host may fold away (the click-twice bug, 2026-10-13).
export type DashPaneRev = number
// The band above the prompt's revision, the same way: the band reads it, a band press bumps it.
export type DashBandRev = number

declare module 'claude-code' {
  interface PluginState {
    dash: { paneRev: DashPaneRev; bandRev: DashBandRev }
  }
}
