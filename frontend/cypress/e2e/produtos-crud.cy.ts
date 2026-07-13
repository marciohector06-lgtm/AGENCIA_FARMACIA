describe("Cadeia de cadastro: Fabricante -> Princípio Ativo -> Produto (backend real)", () => {
  const sufixo = Date.now();
  const nomeFabricante = `Fabricante Cypress ${sufixo}`;
  const nomePrincipio = `Principio Cypress ${sufixo}`;
  const nomeProduto = `Produto Cypress ${sufixo}`;

  it("cadastra um fabricante", () => {
    cy.visit("/fabricantes");
    // "Carregando..." só some depois que o efeito de fetch (client-side) roda,
    // o que só acontece após a hidratação — esperar por isso (em vez de só
    // pelo <h1>, que já vem no HTML do servidor) evita clicar em "+ Novo"
    // antes do onClick estar de fato conectado.
    cy.contains("Carregando...").should("not.exist");
    cy.contains("button", "+ Novo").click();
    cy.get("#nome").type(nomeFabricante);
    cy.contains('button[type="submit"]', "Salvar").click();
    cy.contains(nomeFabricante).should("be.visible");
  });

  it("cadastra um princípio ativo", () => {
    cy.visit("/principios-ativos");
    cy.contains("Carregando...").should("not.exist");
    cy.contains("button", "+ Novo").click();
    cy.get("#nome").type(nomePrincipio);
    cy.get("#classe_terapeutica").type("Analgesico");
    cy.contains('button[type="submit"]', "Salvar").click();
    cy.contains(nomePrincipio).should("be.visible");
  });

  it("cadastra um produto usando os selects dinâmicos de fabricante e princípio ativo", () => {
    cy.visit("/produtos");
    cy.contains("Carregando...").should("not.exist");
    cy.contains("button", "+ Novo").click();
    cy.get("#nome_comercial").type(nomeProduto);
    cy.get("#fabricante_id").select(nomeFabricante);
    cy.get("#principio_ativo_id").select(nomePrincipio);
    cy.get("#forma_farmaceutica").select("comprimido");
    cy.get("#via_administracao").select("oral");
    cy.get("#concentracao_valor").type("500");
    cy.get("#concentracao_unidade").select("mg");
    cy.get("#quantidade_embalagem").type("20");
    cy.get("#tarja").select("isento");
    cy.get("#preco_tabela").type("9.90");
    cy.contains('button[type="submit"]', "Salvar").click();
    cy.contains(nomeProduto).should("be.visible");
    cy.contains("isento").should("be.visible");
  });

  after(() => {
    // produtos e princípios_ativos não têm DELETE por design (FASE 1: dado de
    // farmácia se desativa, não se apaga) — e o fabricante fica preso por FK
    // RESTRICT enquanto o produto existir. A limpeza possível é desativar o
    // produto (ativo=false), igual um dono da farmácia faria de verdade.
    const apiUrl = Cypress.env("apiUrl") || "http://127.0.0.1:8000/api/v1";
    cy.request("GET", `${apiUrl}/produtos`).then((res) => {
      const alvo = (res.body as { id: string; nome_comercial: string }[]).find(
        (p) => p.nome_comercial === nomeProduto,
      );
      if (alvo) {
        cy.request("PATCH", `${apiUrl}/produtos/${alvo.id}`, { ativo: false });
      }
    });
  });
});
