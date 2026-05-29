import { defineConfig } from 'vite'

// Slidev merges this with its own Vite config.
//
// Silence Rolldown's noisy INVALID_ANNOTATION warnings: @vueuse/core (a
// transitive dependency of Slidev we don't control) ships `/* #__PURE__ */`
// comments in positions Rolldown can't use as dead-code-elimination hints.
// The hints are simply ignored — the build is correct — so we drop just that
// one diagnostic and let every other warning through.
function isPureAnnotationNoise(log: { code?: string; message?: string }) {
  return (
    log?.code === 'INVALID_ANNOTATION' ||
    (log?.message?.includes('#__PURE__') ?? false)
  )
}

export default defineConfig({
  build: {
    rollupOptions: {
      // Modern Rolldown/Rollup route diagnostics through onLog…
      onLog(level, log, handler) {
        if (isPureAnnotationNoise(log)) return
        handler(level, log)
      },
      // …and keep onwarn for safety/compatibility.
      onwarn(warning, handler) {
        if (isPureAnnotationNoise(warning)) return
        handler(warning)
      },
    },
  },
})
