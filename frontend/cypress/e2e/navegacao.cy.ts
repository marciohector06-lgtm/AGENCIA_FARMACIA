describe("Navegação do dashboard", () => {
  it("mostra o menu lateral e carrega a home", () => {
    cy.visit("/");
    cy.contains("h1", "Dashboard").should("be.visible");
    cy.contains("Farmácia MAS").should("be.visible");
    cy.get('a[href="/produtos"]').should("be.visible");
    cy.get('a[href="/atendimento"]').should("be.visible");
  });

  it("navega para cada seção pela sidebar sem erros", () => {
    const rotas = [
      { href: "/produtos", titulo: "Produtos" },
      { href: "/principios-ativos", titulo: "Princípios Ativos" },
      { href: "/fabricantes", titulo: "Fabricantes" },
      { href: "/estoque", titulo: "Estoque" },
      { href: "/lotes", titulo: "Lotes" },
      { href: "/filiais", titulo: "Filiais" },
      { href: "/clientes", titulo: "Clientes" },
      { href: "/agentes/analise-estoque", titulo: "Análise de Estoque" },
      { href: "/auditoria", titulo: "Auditoria" },
      { href: "/atendimento", titulo: "Atendimento (Avatar)" },
    ];

    cy.visit("/");
    for (const rota of rotas) {
      cy.get(`a[href="${rota.href}"]`).click();
      cy.url().should("include", rota.href);
      cy.contains("h1", rota.titulo).should("be.visible");
    }
  });
});
