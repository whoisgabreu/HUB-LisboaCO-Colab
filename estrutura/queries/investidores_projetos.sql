CREATE TABLE "plataforma_geral"."investidores_projetos" ( 
  "id" SERIAL,
  "email_investidor" VARCHAR(250) NOT NULL,
  "pipefy_id_projeto" INTEGER NULL,
  "active" BOOLEAN NULL,
  "inactivated_at" DATE NULL,
  "created_at" DATE NULL,
  "cientista" BOOLEAN NULL,
  CONSTRAINT "PK_projetos_investir" PRIMARY KEY ("id", "email_investidor")
);
