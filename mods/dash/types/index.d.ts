// dash's $.state contract. One value: the pane's revision, bumped by every press in the pane.
// The pane reads it while drawing, so a press redraws it at once through the state write
// rather than through an invalidate the host may fold away (the click-twice bug, 2026-10-13).
export type DashPaneRev = number

declare module 'claude-code' {
  interface PluginState {
    dash: { paneRev: DashPaneRev }
  }
}
