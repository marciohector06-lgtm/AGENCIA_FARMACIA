describe("Atendimento (Avatar) — fluxo mockado", () => {
  // O LLM real é pago e sujeito a cota (já vimos isso acontecer de verdade em
  // produção). Um teste E2E não deve depender de uma API externa de terceiros
  // para ser determinístico — aqui mockamos a resposta do backend e testamos
  // só o contrato da UI: renderizar a sugestão e disparar a confirmação de compra.
  const sessaoId = "11111111-1111-1111-1111-111111111111";
  const produtoId = "22222222-2222-2222-2222-222222222222";

  beforeEach(() => {
    cy.visit("/atendimento");
  });

  it("mostra a sugestão do avatar e confirma a compra", () => {
    cy.intercept("POST", "**/chat/atendimento", (req) => {
      if (req.body.confirmar_compra) {
        req.reply({
          statusCode: 200,
          body: {
            sessao_id: sessaoId,
            resposta: "Compra confirmada! Pagamento aprovado e nota fiscal emitida.",
            produtos_sugeridos: [],
            venda_id: "33333333-3333-3333-3333-333333333333",
            log_auditoria_id: "44444444-4444-4444-4444-444444444444",
          },
        });
      } else {
        req.reply({
          statusCode: 200,
          body: {
            sessao_id: sessaoId,
            resposta: "Temos Dipirona 500mg disponível, ótima para dor de cabeça e febre.",
            produtos_sugeridos: [
              {
                produto_id: produtoId,
                nome_comercial: "Dipirona 500mg",
                disponivel: true,
                preco: 12.5,
                motivo_sugestao: "Produto solicitado, disponível em estoque.",
              },
            ],
            venda_id: null,
            log_auditoria_id: "55555555-5555-5555-5555-555555555555",
          },
        });
      }
    }).as("chatAtendimento");

    cy.get("select").first().find("option").its("length").should("be.gt", 1);
    cy.get("select").first().select(1);

    cy.get('input[placeholder*="dor de cabeça"]').type("Estou com dor de cabeça e febre");
    cy.contains("button", "Enviar").click();

    cy.wait("@chatAtendimento");
    cy.contains("Dipirona 500mg disponível").should("be.visible");
    cy.contains("Dipirona 500mg").should("be.visible");
    cy.contains("button", "Confirmar compra").should("be.visible").click();

    cy.wait("@chatAtendimento");
    cy.contains("Compra confirmada!").should("be.visible");
    cy.contains("Venda registrada").should("be.visible");
  });
});
