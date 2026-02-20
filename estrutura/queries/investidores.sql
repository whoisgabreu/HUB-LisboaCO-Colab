CREATE TABLE "plataforma_geral"."investidores" ( 
  "id" SERIAL,
  "nome" VARCHAR(100) NULL,
  "email" VARCHAR(50) NULL,
  "funcao" VARCHAR(50) NULL,
  "senioridade" VARCHAR(50) NULL,
  "squad" VARCHAR(100) NULL,
  "senha" VARCHAR(250) NULL,
  "nivel_acesso" VARCHAR(10) NULL,
  "ativo" BOOLEAN NULL,
  "cpf" VARCHAR(11) NULL,
  "telefone" VARCHAR(15) NULL,
  "nivel" TEXT NULL,
  CONSTRAINT "investidores_pkey" PRIMARY KEY ("id")
);
