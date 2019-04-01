CREATE TABLE "MULTI_TSK"."LOCATIONS" 
   (	"LOCATION_ID" NUMBER(4,0), 
	"STREET_ADDRESS" VARCHAR2(40), 
	"POSTAL_CODE" VARCHAR2(12), 
	"CITY" VARCHAR2(30), 
	"STATE_PROVINCE" VARCHAR2(25), 
	"COUNTRY_ID" CHAR(2)
   ) ;

   COMMENT ON COLUMN "MULTI_TSK"."LOCATIONS"."LOCATION_ID" IS 'Primary key of locations table';
 
   COMMENT ON COLUMN "MULTI_TSK"."LOCATIONS"."STREET_ADDRESS" IS 'Street address of an office, warehouse, or production site of a company.
Contains building number and street name';
 
   COMMENT ON COLUMN "MULTI_TSK"."LOCATIONS"."POSTAL_CODE" IS 'Postal code of the location of an office, warehouse, or production site
of a company. ';
 
   COMMENT ON COLUMN "MULTI_TSK"."LOCATIONS"."CITY" IS 'A not null column that shows city where an office, warehouse, or
production site of a company is located. ';
 
   COMMENT ON COLUMN "MULTI_TSK"."LOCATIONS"."STATE_PROVINCE" IS 'State or Province where an office, warehouse, or production site of a
company is located.';
 
   COMMENT ON COLUMN "MULTI_TSK"."LOCATIONS"."COUNTRY_ID" IS 'Country where an office, warehouse, or production site of a company is
located. Foreign key to country_id column of the countries table.';
 
   COMMENT ON TABLE "MULTI_TSK"."LOCATIONS"  IS 'Locations table that contains specific address of a specific office,
warehouse, and/or production site of a company. Does not store addresses /
locations of customers. Contains 23 rows; references with the
departments and countries tables. ';
 

  CREATE INDEX "MULTI_TSK"."LOC_CITY_IX" ON "MULTI_TSK"."LOCATIONS" ("CITY") 
  ;
 
  CREATE INDEX "MULTI_TSK"."LOC_COUNTRY_IX" ON "MULTI_TSK"."LOCATIONS" ("COUNTRY_ID") 
  ;
 
  CREATE INDEX "MULTI_TSK"."LOC_STATE_PROVINCE_IX" ON "MULTI_TSK"."LOCATIONS" ("STATE_PROVINCE") 
  ;
  
  ALTER TABLE "MULTI_TSK"."LOCATIONS" ADD CONSTRAINT "LOC_C_ID_FK" FOREIGN KEY ("COUNTRY_ID")
	  REFERENCES "MULTI_TSK"."COUNTRIES" ("COUNTRY_ID") ENABLE;
  
  ALTER TABLE "MULTI_TSK"."LOCATIONS" MODIFY ("CITY" CONSTRAINT "LOC_CITY_NN" NOT NULL ENABLE);
 
  ALTER TABLE "MULTI_TSK"."LOCATIONS" ADD CONSTRAINT "LOC_ID_PK" PRIMARY KEY ("LOCATION_ID") ENABLE;
  