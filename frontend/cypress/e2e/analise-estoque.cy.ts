describe("Análise de Estoque — fluxo mockado", () => {
  // Mesma razão do teste de atendimento: o fluxo real aciona Gemini de verdade
  // (Gerente -> Financeiro), custa dinheiro e tem cota diária. Mockamos a
  // resposta do backend para testar o contrato da tela de forma determinística.
  it("roda a análise e mostra as decisões retornadas", () => {
    cy.intercept("POST", "**/agentes/analise-estoque", {
      statusCode: 200,
      body: {
        propostas_geradas: 1,
        aprovadas: 1,
        rejeitadas: 0,
        decisoes: [
          {
            precificacao_id: "66666666-6666-6666-6666-666666666666",
            aprovado: true,
            margem_resultante: 16.67,
            justificativa: "Margem saudável, aprovado para evitar perda do lote.",
          },
        ],
        resumo: "1 proposta analisada: 1 aprovada. Margem de 16.67% considerada saudável.",
        log_auditoria_ids: [
          "77777777-7777-7777-7777-777777777777",
          "88888888-8888-8888-8888-888888888888",
        ],
      },
    }).as("analiseEstoque");

    cy.visit("/agentes/analise-estoque");
    cy.contains("button", "Rodar Análise").click();

    cy.wait("@analiseEstoque");
    cy.contains("Propostas geradas").parent().contains("1");
    cy.contains("Aprovadas").parent().contains("1");
    cy.contains("Rejeitadas").parent().contains("0");
    cy.contains("Margem saudável, aprovado para evitar perda do lote.").should("be.visible");
    cy.contains("Aprovado").should("be.visible");
    cy.contains("16.67%").should("be.visible");
  });
});
