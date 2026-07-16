import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    // Painel administrativo é desktop-only por design (a Sidebar some fora
    // da tela abaixo do breakpoint `lg`=1024px do Tailwind); o viewport
    // default do Cypress (1000x660) cai abaixo disso e testa o layout
    // mobile por engano.
    viewportWidth: 1440,
    viewportHeight: 900,
    env: {
      apiUrl: "http://127.0.0.1:8001/api/v1",
    },
    setupNodeEvents() {},
  },
});
