// vigil's $.state contract. Two values: the pane's revision, bumped by every press in the pane
// and by every typed /rw-vigil view command, and the band's (below).
// The pane reads it while drawing, so a press redraws it at once through the state write
// rather than through an invalidate the host may fold away (the click-twice bug, 2026-10-13).
export type VigilPaneRev = number
// The band above the prompt's revision, the same way: the band reads it, a band press bumps it.
export type VigilBandRev = number

declare module 'claude-code' {
  interface PluginState {
    vigil: { paneRev: VigilPaneRev; bandRev: VigilBandRev }
  }
}
