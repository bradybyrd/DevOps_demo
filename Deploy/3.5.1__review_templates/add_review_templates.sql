--------------------------------------------------------
--  DDL for Table REVIEW_TEMPLATES
--------------------------------------------------------

  CREATE TABLE "REVIEW_TEMPLATES" 
   (	"ID" NUMBER(4,0), 
	"REVIEW_TYPE" VARCHAR2(40), 
	"AUTHOR_ID" NUMBER(4,0), 
	"IS_CURRENT" CHAR(1), 
	"TEMPLATE" VARCHAR2(1000)
   );
 