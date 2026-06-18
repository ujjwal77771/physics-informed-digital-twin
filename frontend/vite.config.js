import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/three'))    return 'three'
          if (id.includes('node_modules/recharts')) return 'recharts'
          if (id.includes('node_modules/react-dom')) return 'react'
          if (id.includes('node_modules/react/'))   return 'react'
          if (id.includes('node_modules/lucide'))   return 'lucide'
        }
      }
    }
  }
})


