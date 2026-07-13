describe("CRUD de Filiais (backend real)", () => {
  const nome = `Filial Cypress ${Date.now()}`;
  // Não pode conter `nome` como substring: cy.contains faz match parcial, e
  // "não existe mais o nome antigo" precisa ser uma checagem que não dê falso
  // negativo por o texto editado ainda conter o texto original.
  const nomeEditado = `Filial Cypress Renomeada ${Date.now()}`;

  it("cria, edita e remove uma filial", () => {
    cy.visit("/filiais");
    // Esperar o fetch inicial (client-side, só roda pós-hidratação) terminar
    // antes de clicar — clicar cedo demais pode acontecer antes do onClick
    // estar conectado.
    cy.contains("Carregando...").should("not.exist");

    // Criar
    cy.contains("button", "+ Novo").click();
    cy.get("#nome").type(nome);
    cy.get("#cidade").type("Curitiba");
    cy.get("#uf").type("PR");
    cy.contains('button[type="submit"]', "Salvar").click();
    cy.contains(nome).should("be.visible");
    cy.contains("Curitiba").should("be.visible");

    // Editar
    cy.contains("tr", nome).contains("Editar").click();
    cy.get("#nome").clear().type(nomeEditado);
    cy.contains('button[type="submit"]', "Salvar").click();
    cy.contains(nomeEditado).should("be.visible");
    cy.contains(nome).should("not.exist");

    // Remover
    cy.on("window:confirm", () => true);
    cy.contains("tr", nomeEditado).contains("Excluir").click();
    cy.contains(nomeEditado).should("not.exist");
  });
});
