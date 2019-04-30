--------------------------------------------------------
--  DDL for Table REVIEWS
--------------------------------------------------------

  CREATE TABLE "REVIEWS" 
   (	"ID" NUMBER(4,0), 
	"REVIEW_TYPE" VARCHAR2(40), 
	"MANAGER_ID" NUMBER(4,0), 
	"EMPLOYEE_ID" NUMBER(4,0), 
	"RATING" VARCHAR2(25), 
	"COMMENTS" VARCHAR2(1000)
   );
 
--------------------------------------------------------
--  DDL for Index REVIEW_MANAGER_ID_IX
--------------------------------------------------------

  CREATE INDEX "REVIEW_MANAGER_ID_IX" ON "REVIEWS" ("MANAGER_ID") ;

--------------------------------------------------------
--  DDL for Index REVIEW_EMPLOYEE_ID_IX
--------------------------------------------------------
  CREATE INDEX "REVIEW_EMPLOYEE_ID_IX" ON "REVIEWS" ("EMPLOYEE_ID") ;

--------------------------------------------------------
--  Constraints for Table REVIEWS
--------------------------------------------------------

  ALTER TABLE "REVIEWS" ADD CONSTRAINT "REVIEW_ID_PK" PRIMARY KEY ("ID");
  
 

