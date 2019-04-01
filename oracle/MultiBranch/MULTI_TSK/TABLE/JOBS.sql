CREATE TABLE "MULTI_TSK"."JOBS" 
   (	"JOB_ID" VARCHAR2(10), 
	"JOB_TITLE" VARCHAR2(35), 
	"MIN_SALARY" NUMBER(6,0), 
	"MAX_SALARY" NUMBER(6,0)
   ) ;

   COMMENT ON COLUMN "MULTI_TSK"."JOBS"."JOB_ID" IS 'Primary key of jobs table.';
 
   COMMENT ON COLUMN "MULTI_TSK"."JOBS"."JOB_TITLE" IS 'A not null column that shows job title, e.g. AD_VP, FI_ACCOUNTANT';
 
   COMMENT ON COLUMN "MULTI_TSK"."JOBS"."MIN_SALARY" IS 'Minimum salary for a job title.';
 
   COMMENT ON COLUMN "MULTI_TSK"."JOBS"."MAX_SALARY" IS 'Maximum salary for a job title';
 
   COMMENT ON TABLE "MULTI_TSK"."JOBS"  IS 'jobs table with job titles and salary ranges. Contains 19 rows.
References with employees and job_history table.';
 
  
  ALTER TABLE "MULTI_TSK"."JOBS" MODIFY ("JOB_TITLE" CONSTRAINT "JOB_TITLE_NN" NOT NULL ENABLE);
 
  ALTER TABLE "MULTI_TSK"."JOBS" ADD CONSTRAINT "JOB_ID_PK" PRIMARY KEY ("JOB_ID") ENABLE;
  