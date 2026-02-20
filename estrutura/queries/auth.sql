CREATE TABLE "plataforma_geral"."auth" ( 
  "id" SERIAL,
  "email" VARCHAR(50) NOT NULL,
  "token" VARCHAR(30) NULL,
  CONSTRAINT "PK_auth" PRIMARY KEY ("id", "email"),
  CONSTRAINT "unique_email" UNIQUE ("email")
);
