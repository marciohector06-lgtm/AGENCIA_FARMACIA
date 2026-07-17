describe("Totem — avatar em tela cheia, fluxo mockado", () => {
  const sessaoId = "11111111-1111-1111-1111-111111111111";
  const produtoId = "22222222-2222-2222-2222-222222222222";

  beforeEach(() => {
    cy.visit("/totem");
  });

  it("esconde seletor de filial/cliente, texto fica atrás do ícone de teclado, e roda o fluxo de compra", () => {
    cy.get("select").should("not.exist");
    // Voz é o principal — campo de texto só aparece depois de tocar no teclado.
    cy.get('input[placeholder="Digite sua dúvida..."]').should("not.exist");

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

    cy.get('button[aria-label="Digitar em vez de falar"]').click();
    cy.get('input[placeholder="Digite sua dúvida..."]').type("Estou com dor de cabeça e febre");
    cy.contains("button", "Enviar").click();

    cy.wait("@chatAtendimento");
    // Card de produto substitui a legenda quando ela sugere algo.
    cy.contains("Dipirona 500mg").should("be.visible");
    cy.contains("R$ 12.50").should("be.visible");
    cy.contains("button", "Confirmar compra").should("be.visible").click();

    cy.wait("@chatAtendimento");
    // Card some depois de confirmar; a resposta dela vira legenda.
    cy.contains("button", "Confirmar compra").should("not.exist");
    cy.contains("Compra confirmada!").should("be.visible");

    // DELAY_APOS_VENDA_MS (6s): a tela reseta sozinha para o próximo cliente
    // (key remonta TotemAvatarExperience — mensagens, legenda e teclado
    // aberto voltam todos ao estado inicial).
    cy.contains("Compra confirmada!", { timeout: 8000 }).should("not.exist");
    cy.get('input[placeholder="Digite sua dúvida..."]').should("not.exist");
  });

  it("botão 'Falar com farmacêutico' desativa a IA sem chamar o backend", () => {
    cy.intercept("POST", "**/chat/atendimento").as("chatAtendimento");

    cy.contains("button", "Falar com farmacêutico").click();
    cy.contains("Um momento, o farmacêutico já vem até você.").should("be.visible");
    // Nenhuma chamada de rede — é só UX local, como especificado.
    cy.get("@chatAtendimento.all").should("have.length", 0);

    cy.contains("button", "Voltar ao atendimento por IA").click();
    cy.contains("Um momento, o farmacêutico já vem até você.").should("not.exist");
  });
});
