# Seros Database Table Index
# 518 tables grouped by module prefix
# Full column details: db_schema_full.txt

## Ctrl (3 tables)
  Ctrl_Ntbr_Emp | PK: Ntbr_Emp_Id | Ntbr_Emp_Id, Emp_Id, Pan, Ntbr_Emp_Dob, Ntbr_Cnfm_Dt, Remark, Ntbr_Approved_By, Ntbr_Scan_Path, ... (+2 more)
  Ctrl_Ntbr_Fs | PK: Ntbr_Fs_Id | Ntbr_Fs_Id, Fs_Emp_Id, Ntbr_Fs_Cdc_No, Pan, Ntbr_Fs_Dob, Ntbr_Cnfm_Dt, Remark, Ntbr_Approved_By, ... (+8 more)
  Ctrl_Passport | PK: Ctrl_PP_Id | Ctrl_PP_Id, PP_No, IT_System_id, Business_System_id, Tbl_Abrv

## EBS (1 tables)
  EBS_Error_Description_DB | PK: Constraint_Name | Constraint_Name, Description, Table_Name

## EF (4 tables)
  EF_Product | PK: ProductID | ProductID, ProductName, Price
  EF_Stock | PK: StockID | StockID, ProductID, Count
  EF_User | PK: EF_User_Id | EF_User_Id, EF_User_UserID, EF_User_Password
  EF_UserTemp | PK: UserId | UserId, UserName, Password

## Fs (2 tables)
  Fs_Basic_Dtl | PK: None | Fs_Basic_Id, Fs_Emp_Id, Rank_Id, Fs_Category_Id, Emp_Type_Id, Cert_Level, Basic_From, Basic_Amt, ... (+9 more)
  Fs_Catg_To_Rank_Mapping | PK: None | Fs_Catg_To_Rank_Mapping_Id, Fs_Category_Id, Vessel_Dept_Id, Rank_Id, Rank_Order, Business_System_Id_2, Business_System_Id_5, Business_System_Id_6, ... (+5 more)

## Global (1 tables)
  Global_Vsl_Cert_Dtl | PK: Global_Vsl_Cert_Dtl_Id | Global_Vsl_Cert_Dtl_Id, Vessel_Id, Vsl_Cert_Id, Vsl_Cert_Dt, Vsl_Cert_Valid_Till, Last_Survey_Dt, CR_USER_ID, CR_DT, ... (+2 more)

## Loc (1 tables)
  Loc_Name_Variation | PK: None | Loc_Name_Variation_Id, Location_Id, Loc_Diff_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt

## Mail (3 tables)
  Mail_Alert_Dtl | PK: Alert_Id | Alert_Id, Business_System_Id, Alert_Type, Alert_Category, Alert_Name, Alert_Window, Alert_Freq, Menu_Id, ... (+11 more)
  Mail_Alert_To_User | PK: Mail_Alert_To_User_Id | Mail_Alert_To_User_Id, Alert_Id, EMP_ID, EMAIL_Addr, Read_Receipt, Mail_Alert_From, Mail_Alert_To, Addressee_Type, ... (+5 more)
  Mail_MailServ_Dtl | PK: None | Mail_Serv_Name, From_Addr, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT

## Mst (151 tables)
  Mst_Activity | PK: Activity_Id | Activity_Id, Activity_Name, Activity_Type, Activity_Nature, Activity_Location, Intimate_Vessel, Activity_Validity_Days, Business_System_Id_2, ... (+12 more)
  Mst_Bank | PK: Bank_id | Bank_id, Bank_Name, bank_Abrv, Bank_FROM, Bank_TO, Bank_ACTIVE, cr_user_id, cr_dt, ... (+2 more)
  Mst_Bank_Branch | PK: Bank_Br_id | Bank_Br_id, Bank_id, Bank_Br_Name, bank_Br_Addr, Swift_Id, IFSC_Code, IBAN_CPF_No, Correspondent_Bank, ... (+7 more)
  Mst_Bd_Project | PK: Bd_Project_Id | Bd_Project_Id, Bd_Project_Name, Bd_Project_Abrv, Bd_Project_Descr, Location_Id, Company_Id, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_Bidding_Stages | PK: Bidding_Stages_Id | Bidding_Stages_Id, Bidding_Stages_Name, Bidding_Stages_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Broker | PK: Broker_Id | Broker_Id, Broker_Name, Broker_Addr, Broker_Tel, Broker_Fax, Broker_Mobile_No, Broker_Email, Business_System_Id_2, ... (+5 more)
  Mst_Bunker | PK: Bunker_Id | Bunker_Id, Bunker_Name, Bunker_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Business_Grp | PK: BUSINESS_GRP_ID | BUSINESS_GRP_ID, BUSINESS_GRP_NAME, Parent_Business_Grp_Id, BUSINESS_GRP_ABRV, BUSINESS_GRP_ORDER, BUSINESS_GRP_FROM, BUSINESS_GRP_TO, BUSINESS_GRP_ACTIVE, ... (+4 more)
  Mst_Business_Report | PK: Business_Report_Id | Business_Report_Id, Business_Report_Name, Business_Grp_Id, Report_Freq_Days, Month_End_Report, DMS_Path, Business_Report_Active, Cr_User_Id, ... (+3 more)
  Mst_Business_System | PK: Business_System_id | Business_System_id, Buss_System_Dtl, Buss_System_Abrv, Buss_System_Schema_Name, Mail_From_Address, Mail_User_Name, Mail_User_Password, Owner_Emp_Id, ... (+4 more)
  Mst_Business_System_User_Mapping | PK: Buss_System_User_Mapping_id | Buss_System_User_Mapping_id, Business_System_id, User_Id, Buss_System_User_Mapping_From, Buss_System_User_Mapping_To, Buss_System_User_Mapping_Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_Business_Vertical | PK: Business_Vertical_Id | Business_Vertical_Id, Business_Vertical_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Buss_Cert | PK: Buss_Cert_Id | Buss_Cert_Id, Buss_Cert_Name, Buss_Cert_Type_Id, Buss_Cert_Validity, Business_System_Id_2, Business_System_Id_5, Business_System_Id_6, Business_System_Id_7, ... (+8 more)
  Mst_Buss_Cert_Issue_Authority | PK: Buss_Cert_Issue_Auth_Id | Buss_Cert_Issue_Auth_Id, Buss_Cert_Issue_Authority, Buss_Cert_Issue_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Buss_Cert_Type | PK: Buss_Cert_Type_Id | Buss_Cert_Type_Id, Buss_Cert_Type, Buss_Cert_Type_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Buss_Grp_System_Mapping | PK: None | Buss_Grp_System_Mapping_Id, Business_Grp_Id, Business_System_id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_CSR_Area | PK: CSR_Area_Id | CSR_Area_Id, CSR_Area_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_CSR_Commodity | PK: CSR_Commodity_Id | CSR_Commodity_Id, CSR_Commodity_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Cargo_Subtype | PK: Cargo_Subtype_Id | Cargo_Subtype_Id, Cargo_Type_Id, Cargo_Subtype, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Cargo_Type | PK: Cargo_Type_Id | Cargo_Type_Id, Cargo_Type, Color_Indication, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Cert | PK: cert_id | cert_id, cert_type_id, cert_name, cert_abrv, vessel_dept_id, Cert_Training_Type, Business_System_Id_2, Business_System_Id_6, ... (+4 more)
  Mst_Cert_Type | PK: cert_type_id | cert_type_id, cert_type_name, cert_type_abrv, cr_user_id, cr_dt, mod_user_id, mod_dt
  Mst_Charterer | PK: Charterer_Id | Charterer_Id, Charterer_Name, Charterer_Type, Charterer_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Committee | PK: Committee_Id | Committee_Id, Committee_Name, Committee_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Company | PK: COMPANY_ID | COMPANY_ID, Organisational_Grp_Id, Business_Grp_Id, Company_Name, Parent_Company_Id, Company_ABRV, Company_Code, Country_Id, ... (+15 more)
  Mst_Company_Act | PK: Company_Act_Id | Company_Act_Id, Section_No, Provision_Headline, Section_Order, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Company_CEO | PK: None | Company_CEO_Id, Company_Id, Emp_Id, CEO_From, CEO_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Company_Hst | PK: None | Company_Id, Business_Grp_Id, Company_Name, Parent_Company_Id, Company_Dispname, Company_Abrv, Country_Id, Currency_Id, ... (+6 more)
  Mst_Company_Location | PK: Company_Loc_Id | Company_Loc_Id, Company_Loc_NAME, Company_Loc_ABRV, Company_Loc_Address, Location_Id, Postal_Code, Country_Id, Latitude, ... (+11 more)
  Mst_Company_Type | PK: Company_Type_Id | Company_Type_Id, Company_Id, Company_Type, Company_Type_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Container_Size | PK: Container_Size_Id | Container_Size_Id, Container_Size, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Container_Type | PK: Container_Type_Id | Container_Type_Id, Container_Type, Container_Type_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Continent | PK: Continent_Id | Continent_Id, Continent_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Country | PK: country_id | country_id, country_name, Country_Known_Name, Country_ISO_Cd, Continent_Id, country_active, cr_user_id, cr_dt, ... (+2 more)
  Mst_Country_State | PK: country_state_id | country_state_id, country_id, country_state_name, country_state_abrv, country_state_active, cr_user_id, cr_dt, mod_user_id, ... (+1 more)
  Mst_Currency | PK: Currency_Id | Currency_Id, Currency_Name, Currency_Abrv, Decimal_Name, Currency_Text, Currency_Active, CR_USER_ID, CR_DT, ... (+2 more)
  Mst_Customer | PK: Customer_Id | Customer_Id, Customer_Name, Country_Id, Location_Id, Business_System_Id_7, Business_System_Id_9, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_DashboardHeaders | PK: None | DashboardHeader, DashboardID, OrderNo
  Mst_Delay_Responsibility | PK: Delay_Responsibility_Id | Delay_Responsibility_Id, Delay_Responsibility, Business_System_Id_8, Business_System_Id_9, Business_System_Id_13, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Department | PK: Dept_Id | Dept_Id, Dept_Name, Dept_Dispname, Dept_Abrv, Dept_Order, Dept_Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_ED_Type | PK: ED_Type_Id | ED_Type_Id, ED_Type_Name, ED_Type_Abrv, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_Emp_Grade | PK: Emp_Grade_Id | Emp_Grade_Id, Emp_Grade, Emp_Designation, Emp_Grade_Order, Emp_Grade_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Emp_Nature | PK: emp_nature_id | emp_nature_id, emp_nature_name, cr_user_id, cr_dt, mod_user_id, mod_dt
  Mst_Emp_Type | PK: emp_type_id | emp_type_id, emp_nature_id, emp_type_name, Currency_Id, Business_System_Id_2, Business_System_Id_5, Business_System_Id_6, Business_System_Id_11, ... (+5 more)
  Mst_Employee | PK: EMP_ID | EMP_ID, COMPANY_ID, DEPT_ID, COMPANY_LOC_ID, Emp_Fname, Emp_Mname, Emp_Sname, EMP_TITLE, ... (+17 more)
  Mst_Environmental_Params | PK: Env_Params_Id | Env_Params_Id, Env_Params_Name, Measurement_Unit_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_External_Agency | PK: External_Agency_Id | External_Agency_Id, External_Agency_Name, External_Agency_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_FY_Month | PK: None | FY_Month_Id, FY_Month_No, FY_Month_Name, FY_Month_Abrv, FY_Quarter_Id, FY_Season_Id, Cal_Quarter_Id, Cr_User_Id, ... (+3 more)
  Mst_FY_Quarter | PK: FY_Quarter_Id | FY_Quarter_Id, FY_Quarter, FY_Quarter_Text, Country_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_FY_Season | PK: FY_Season_Id | FY_Season_Id, FY_Season, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Financial_Year | PK: Financial_Year_Id | Financial_Year_Id, Fin_Year_From, Fin_Year_To, Fin_Year_Text, Fin_Year_Subtext, Assessment_Year, NRI_Days, Fin_Year_Status, ... (+4 more)
  Mst_Freight_Forwarder | PK: Freight_Forwarder_Id | Freight_Forwarder_Id, Freight_Forwarder_Name, Country_Id, Location_Id, Business_System_Id_2, Business_System_Id_5, Business_System_Id_7, Business_System_Id_8, ... (+4 more)
  Mst_Fs_Category | PK: fs_category_id | fs_category_id, fs_category_name, Business_System_Id_2, Business_System_Id_5, Business_System_Id_6, Business_System_Id_11, Business_System_Id_16, cr_user_id, ... (+3 more)
  Mst_Fs_Catg_To_SSType | PK: catg_sstype_id | catg_sstype_id, fs_category_id, emp_type_id, serv_type_id, serv_subtype_id, Business_System_Id_2, Business_System_Id_5, Business_System_Id_6, ... (+5 more)
  Mst_Fs_Leave_Type | PK: Fs_Leave_Type_Id | Fs_Leave_Type_Id, Fs_Leave_Type_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_GL_Acct_L1Grp | PK: GL_Acct_L1Grp_Id | GL_Acct_L1Grp_Id, GL_Acct_L1Grp_Name, GL_Code_From, GL_Code_To, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_GL_Acct_L2Grp | PK: GL_Acct_L2Grp_Id | GL_Acct_L2Grp_Id, GL_Acct_L2Grp_Name, GL_Acct_L1Grp_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_GL_Acct_L3Grp | PK: GL_Acct_L3Grp_Id | GL_Acct_L3Grp_Id, GL_Acct_L3Grp_Name, GL_Acct_L2Grp_Id, GL_Acct_L1Grp_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_GL_Acct_L3Grp_Co_Mapping | PK: L3Grp_Co_Map_Id | L3Grp_Co_Map_Id, GL_Acct_L3Grp_Id, Company_Id, Business_Grp_Id, L3Grp_Co_Map_From, L3Grp_Co_Map_To, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_GL_Acct_L4Grp | PK: GL_Acct_L4Grp_Id | GL_Acct_L4Grp_Id, GL_Acct_L4Grp_Name, GL_Acct_L3Grp_Id, GL_Acct_L2Grp_Id, GL_Acct_L1Grp_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_GL_Code | PK: GL_Code_Id | GL_Code_Id, GL_Code, GL_Acct_Name, GL_Acct_L4Grp_Id, GL_Acct_L3Grp_Id, GL_Acct_L2Grp_Id, GL_Acct_L1Grp_Id, GL_Code_Type, ... (+4 more)
  Mst_Global_Co_Vertical_Mapping | PK: Global_Co_Vert_Map_Id | Global_Co_Vert_Map_Id, Global_Company_Id, Business_Vertical_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Global_Company | PK: Global_Company_Id | Global_Company_Id, Global_Company_Name, Country_Id, Global_Company_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_IT_Accessory | PK: IT_Accessory_Id | IT_Accessory_Id, IT_Accessory_Name, IT_Accessory_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_IT_Appl_Category | PK: IT_Appl_Category_Id | IT_Appl_Category_Id, IT_Appl_Category, IT_Appl_Category_Order, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_IT_Application_Type | PK: IT_Appl_Type_Id | IT_Appl_Type_Id, IT_Appl_Type, Max_Resources, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_IT_Asset_Mfg | PK: IT_Asset_Mfg_id | IT_Asset_Mfg_id, IT_Asset_Mfg, IT_Asset_Mfg_ACTIVE, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_IT_Asset_Model | PK: IT_Asset_Model_id | IT_Asset_Model_id, IT_Asset_Mfg_id, IT_Asset_SubType_id, IT_Asset_Model, IT_Asset_Model_Active, CR_USER_ID, CR_DT, MOD_USER_ID, ... (+1 more)
  Mst_IT_Asset_SubType | PK: it_asset_SubType_id | it_asset_SubType_id, it_asset_type_id, it_asset_SubType, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_IT_Asset_Type | PK: it_asset_type_id | it_asset_type_id, it_asset_type, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_IT_Cess_Slabs | PK: None | IT_Cess_Slab_Id, IT_Cess_Slab_From, Income_From, Income_To, IT_Cess_Prcnt, IT_Cess_Slab_To, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_IT_Section | PK: IT_Sec_Id | IT_Sec_Id, IT_Sec_Name, IT_Sec_Abrv, ITax_Grp_Id, IT_Sec_Max_Amt, IT_Sec_Rebate_Percentage, IT_Sec_Rebate_Amt, IT_Sec_Reduce_Taxable_Amt, ... (+6 more)
  Mst_IT_Slabs | PK: None | IT_Slab_Id, IT_Slab_From, Age_From, Age_To, Gender, Income_From, Income_To, IT_Prcnt, ... (+6 more)
  Mst_IT_Surcharge_Slabs | PK: None | IT_SC_Slab_Id, IT_SC_Slab_From, Income_From, Income_To, IT_SC_Prcnt, IT_SC_Slab_To, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_ITax_Group | PK: ITax_Grp_Id | ITax_Grp_Id, ITax_Grp_Name, ITax_Grp_Abrv, ITax_Grp_Related_To, ITax_Grp_Action, ITax_Grp_Order, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_InCharter_Type | PK: InCharter_Type_Id | InCharter_Type_Id, InCharter_Type, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_InCharter_Vsl | PK: InCharter_Vsl_Id | InCharter_Vsl_Id, InChartering_Company_Id, Business_System_Id, Vessel_Id, Vessel_Subtype_Id, Vessel_Name, Vsl_Charter_Type_Id, Vsl_SubCharter_Co_Id, ... (+13 more)
  Mst_Insp_Act_Footnote | PK: Insp_Act_Footnote_Id | Insp_Act_Footnote_Id, Insp_Act_Footnote_Name, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_Insp_Action | PK: Insp_Action_Id | Insp_Action_Id, Insp_Action_Code, Insp_Act_Footnote_Id, Insp_Action_Name, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_Insp_Deficiency | PK: Insp_Deficiency_Id | Insp_Deficiency_Id, Insp_Deficiency_Code, Insp_Deficiency_Name, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_Insp_MOU | PK: Insp_MOU_Id | Insp_MOU_Id, Insp_MOU_Name, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_Insp_SubDeficiency | PK: Insp_SubDeficiency_Id | Insp_SubDeficiency_Id, Insp_Deficiency_Id, Insp_SubDeficiency_Code, Insp_SubDeficiency_Name, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_Insp_Type | PK: Insp_Type_Id | Insp_Type_Id, Insp_Type_Code, Insp_Type_Name, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_Leaving_Reason | PK: leaving_reason_id | leaving_reason_id, leaving_reason, cr_user_id, cr_dt, mod_user_id, mod_dt
  Mst_Leaving_Reason_Dtl | PK: leaving_reason_dtl_id | leaving_reason_dtl_id, leaving_reason_id, leaving_reason_dtl, cr_user_id, cr_dt, mod_user_id, mod_dt
  Mst_Liquid_Cargo | PK: Liquid_Cargo_Id | Liquid_Cargo_Id, Liquid_Cargo, Liquid_Cargo_Type_Id, Liquid_Cargo_Grp_Id, Measurement_Unit_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Liquid_Cargo_Grp | PK: Liquid_Cargo_Grp_Id | Liquid_Cargo_Grp_Id, Liquid_Cargo_Grp, Liquid_Cargo_Type_Id, Measurement_Unit_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Liquid_Cargo_Type | PK: Liquid_Cargo_Type_Id | Liquid_Cargo_Type_Id, Liquid_Cargo_Type, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Location | PK: Location_Id | Location_Id, Country_Id, Country_State_Id, Location_Name, location_active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Lubricant_Grade | PK: Lubricant_Grade_Id | Lubricant_Grade_Id, Lubricant_Grade, Lubricant_Type_Id, Business_System_id_2, Business_System_id_7, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Lubricant_Type | PK: Lubricant_Type_Id | Lubricant_Type_Id, Lubricant_Type, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Marine_Courses | PK: marine_course_id | marine_course_id, marine_course_name, marine_course_duration, marine_course_active, cr_user_id, cr_dt, mod_user_id, mod_dt
  Mst_Marine_Doctor | PK: Marine_Doctor_Id | Marine_Doctor_Id, Doctor_Name, Doctor_Addr, Doctor_Tel, Doctor_Fax, Doctor_Mobile_No, Doctor_Email, Doctor_From_Dt, ... (+5 more)
  Mst_Marine_Inst_Course | PK: marine_inst_course_id | marine_inst_course_id, marine_inst_id, marine_course_id, marine_inst_course_active, cr_user_id, cr_dt, mod_user_id, mod_dt
  Mst_Marine_Institutes | PK: marine_inst_id | marine_inst_id, marine_inst_name, marine_inst_addr, location_id, marine_inst_tel, marine_inst_fax, marine_inst_email, Marine_Inst_Website, ... (+6 more)
  Mst_Marine_Mdl_Test | PK: Mdl_Test_Id | Mdl_Test_Id, Mdl_Test, Mdl_Test_Type, Mdl_Test_Rate, Mdl_Test_Validity_Days, Mdl_Rate_From_Dt, Mdl_Rate_To_Dt, CR_USER_ID, ... (+3 more)
  Mst_Measurement_Unit | PK: Measurement_Unit_Id | Measurement_Unit_Id, Measurement_Unit, Measurement_Unit_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Menu | PK: Menu_Id | Menu_Id, Business_System_id, Menu_Title, Menu_Descr, Menu_Url, Menu_Parent_Id, Menu_ORDER, Menu_Type, ... (+13 more)
  Mst_Operation_Delay | PK: Operation_Delay_Id | Operation_Delay_Id, Operation_Delay, Business_System_Id_8, Business_System_Id_9, Business_System_Id_13, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Organisational_Grp | PK: Organisational_Grp_Id | Organisational_Grp_Id, Organisational_Grp_Name, Organisational_Grp_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Port | PK: port_id | port_id, port_name, country_id, location_id, Currency_Id, Latitude, Longitude, port_active, ... (+4 more)
  Mst_Port_Delay | PK: Port_Delay_Id | Port_Delay_Id, Port_Delay_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Port_Distance | PK: Port_Distance_Id | Port_Distance_Id, From_Port_Id, To_Port_Id, Nautical_Miles, Est_Days_13k, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Port_Terminals | PK: Port_Terminal_Id | Port_Terminal_Id, Port_Id, Terminal_Name, Terminal_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Primary_Buss_Grp | PK: None | Primary_Business_Grp_Id, Primary_Business_Grp_Name, Primary_Business_Grp_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Project | PK: Project_Id | Project_Id, Project_Name, Project_Abrv, Project_Descr, Location_Id, Company_Id, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_Project_Stage | PK: Project_Stage_Id | Project_Stage_Id, Project_Stage_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Qualification | PK: Qualification_Id | Qualification_Id, Qualification_Name, Qualification_Abrv, Qualification_Type, Business_System_Id_2, Business_System_Id_6, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_Rank | PK: rank_id | rank_id, fs_category_id, vessel_dept_id, rank_name, rank_abrv, rank_order, Business_System_Id_2, Business_System_Id_5, ... (+6 more)
  Mst_Relation_Dtl | PK: relation_id | relation_id, relation, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  Mst_Rig_Subtype | PK: Rig_Subtype_Id | Rig_Subtype_Id, Rig_Subtype_Name, Rig_Type_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Rig_Type | PK: Rig_Type_Id | Rig_Type_Id, Rig_Type_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_SAP_Module_Category | PK: SAP_Module_Category_Id | SAP_Module_Category_Id, SAP_Module_Category, SAP_Module_Category_Order, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_SAP_Sub_Modules | PK: SAP_Sub_Module_Id | SAP_Sub_Module_Id, SAP_Sub_Module, SAP_Module_Id, SAP_Sub_Module_Abrv, SAP_Sub_Module_Particulars, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Sap_Client | PK: Sap_Client_Id | Sap_Client_Id, Sap_Client_No, Sap_Client_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Sap_Modules | PK: Sap_Module_Id | Sap_Module_Id, Sap_Module, IT_Appl_Category_Id, Sap_Module_Abrv, SAP_Module_Particulars, Max_Resources, SAP_Module_Type, SAP_Module_Order, ... (+5 more)
  Mst_Sap_Roles | PK: Sap_Role_Id | Sap_Role_Id, Sap_Role_Code, Sap_Role_Descr, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Sap_System | PK: Sap_System_Id | Sap_System_Id, Sap_System, Sap_System_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Sap_Tcodes | PK: Sap_Tcode_Id | Sap_Tcode_Id, Sap_Tcode, Sap_Tcode_Descr, Read_Available, Modify_Available, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_Serv_Subtype | PK: serv_subtype_id | serv_subtype_id, serv_subtype_name, serv_subtype_abrv, Business_System_Id_2, Business_System_Id_6, cr_user_id, cr_dt, mod_user_id, ... (+1 more)
  Mst_Serv_Type | PK: serv_type_id | serv_type_id, serv_type_name, serv_type_abrv, Business_System_Id_2, Business_System_Id_6, cr_user_id, cr_dt, mod_user_id, ... (+1 more)
  Mst_Ship_Co | PK: ship_co_id | ship_co_id, ship_co_name, ship_co_abrv, country_id, cr_user_id, cr_dt, mod_user_id, mod_dt
  Mst_Shipping_Agent | PK: Shipping_Agent_Id | Shipping_Agent_Id, Shipping_Agent_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Surveyor | PK: Surveyor_Id | Surveyor_Id, Surveyor_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Training_Area | PK: Training_Area_Id | Training_Area_Id, Training_Area_Name, Training_Type_Id, Cr_User_Id, Cr_dt, Mod_User_Id, Mod_Dt
  Mst_Training_Type | PK: Training_Type_Id | Training_Type_Id, Training_Type_Name, Cr_User_Id, Cr_dt, Mod_User_Id, Mod_Dt
  Mst_Transport_Type | PK: Transport_Type_Id | Transport_Type_Id, Transport_Type, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Transporter | PK: Transporter_Id | Transporter_Id, Transporter_Name, Business_System_Id_6, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Unit_Conversion | PK: None | Unit_Conversion_Id, Liquid_Cargo_Id, From_Measurement_Unit_Id, To_Measurement_Unit_Id, Conversion_Factor, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Mst_User | PK: USER_ID | USER_ID, USER_NAME, EMP_ID, NONEMP_ID, DEPT_ID, USER_LOGIN_ID, USER_ACTIVE, USER_TYPE_ID, ... (+8 more)
  Mst_User_Password | PK: None | USER_ID, PWD, PASSWORD_DATE, USER_PASSWORD, PASSWORD_TEXT
  Mst_Vehicle_Subtype | PK: Vehicle_Subtype_Id | Vehicle_Subtype_Id, Vehicle_Type_Id, Vehicle_Subtype_Name, Vehicle_Subtype_Abrv, Vehicle_Subtype_Desc, Business_System_Id_6, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mst_Vehicle_Type | PK: Vehicle_Type_Id | Vehicle_Type_Id, Vehicle_Type_Name, Vehicle_Type_Desc, Business_System_Id_6, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vendor_Type | PK: Vendor_Type_Id | Vendor_Type_Id, Vendor_Type, Vendor_Type_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vessel | PK: Vessel_Id | Vessel_Id, Vessel_Type_Id, Vessel_Subtype_Id, Vessel_Name, Own_Ship_Co_Id, Mgr_Ship_Co_Id, Imo_No, MMSI_No, ... (+29 more)
  Mst_Vessel_Deficiency | PK: Vessel_Deficiency_Id | Vessel_Deficiency_Id, Vessel_Deficiency_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vessel_Dept | PK: vessel_dept_id | vessel_dept_id, vessel_dept_name, vessel_dept_order, Business_System_Id_2, Business_System_Id_5, Business_System_Id_6, Business_System_Id_11, cr_user_id, ... (+3 more)
  Mst_Vessel_Manager_Hst | PK: None | Vessel_Id, Old_Mgr_Ship_Co_Id, Old_Mgr_Ship_Co_From, Old_Mgr_Ship_Co_To, Cr_User_Id, Cr_Dt
  Mst_Vessel_Name_Hst | PK: None | Vessel_Id, Vessel_Name, Old_Name_From, Old_Name_To, Cr_User_Id, Cr_Dt
  Mst_Vessel_Owner_Hst | PK: None | Vessel_Id, Old_Own_Ship_Co_Id, Old_Own_Ship_Co_From, Old_Own_Ship_Co_To, Cr_User_Id, Cr_Dt
  Mst_Vessel_Shifting_Cause | PK: Vessel_Shifting_Cause_Id | Vessel_Shifting_Cause_Id, Vessel_Shifting_Cause, Business_System_Id_8, Business_System_Id_9, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vessel_Subtype | PK: vessel_subtype_id | vessel_subtype_id, vessel_type_id, vessel_subtype_name, vessel_subtype_active, vessel_subtype_order, cr_user_id, cr_dt, mod_user_id, ... (+1 more)
  Mst_Vessel_Type | PK: vessel_type_id | vessel_type_id, vessel_type_name, vessel_type_abrv, cr_user_id, cr_dt, mod_user_id, mod_dt
  Mst_Visa_Process_Info | PK: Visa_Process_Info_Id | Visa_Process_Info_Id, Country_Id, Processing_Location_Id, Visa_Process_Days, Cr_User_Id, Cr_dt, Mod_User_Id, Mod_Dt
  Mst_Vsl_Charter_Type | PK: Vsl_Charter_Type_Id | Vsl_Charter_Type_Id, Vsl_Charter_Type, Vsl_Charter_Type_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vsl_Classification_Society | PK: Vsl_Class_Soc_Id | Vsl_Class_Soc_Id, Vsl_Class_Soc, Vsl_Class_Soc_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vsl_Insu_Risk_Type | PK: Vsl_Insu_Risk_Type_Id | Vsl_Insu_Risk_Type_Id, Vsl_Insu_Risk_Type, Vsl_Insu_Risk_Type_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vsl_Insu_Underwriter | PK: Vsl_Insu_Underwriter_Id | Vsl_Insu_Underwriter_Id, Vsl_Insu_Underwriter_Name, Country_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vsl_Insurance_Clubs | PK: Vsl_Insu_Club_Id | Vsl_Insu_Club_Id, Vsl_Insu_Club, Vsl_Insu_Club_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Vsl_Insurance_Type | PK: Vsl_Insu_Type_Id | Vsl_Insu_Type_Id, Vsl_Insu_Type, Vsl_Insu_Type_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mst_Working_Designation | PK: Working_Designation_Id | Working_Designation_Id, Working_Designation, Critical_Flag, Usage_Filter, Working_Designation_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)

## Mstx (9 tables)
  Mstx_Equip_Cert_Authority | PK: Equip_Cert_Auth_Id | Equip_Cert_Auth_Id, Equip_Cert_Auth, Business_System_Id_6, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mstx_Incident_Cause | PK: Incident_Cause_Id | Incident_Cause_Id, Incident_Cause_Desc, Incident_Cause_Category, Business_System_Id_6, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mstx_Incident_Subcause | PK: Incident_Subcause_Id | Incident_Subcause_Id, Incident_Subcause, Incident_Cause_Id, Business_System_Id_6, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mstx_Incident_Type | PK: Incident_Type_Id | Incident_Type_Id, Incident_Type, Incident_Abrv, Business_System_Id_6, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mstx_Injury_Type | PK: Injury_Type_Id | Injury_Type_Id, Injury_Type, Cr_User_Id, Cr_dt, Mod_User_Id, Mod_Dt
  Mstx_Training_Subject | PK: Training_Subject_Id | Training_Subject_Id, Training_Subject, Training_Area_Id, Training_Type_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  Mstx_Vehicle | PK: Vehicle_Id | Vehicle_Id, Vehicle_No, Vehicle_Only_No, Vehicle_Type_Id, Vehicle_Subtype_Id, Owner_Status, Cr_User_Id, Cr_Dt, ... (+2 more)
  Mstx_Vendor | PK: Vendor_Id | Vendor_Id, Vendor_Name, Vendor_Type_Id, Vendor_SAP_Code, Vendor_Address, Country_id, Vendor_Tel_No, Vendor_Email, ... (+12 more)
  Mstx_Work_Location | PK: Work_Location_Id | Work_Location_Id, Work_Location, Business_System_Id_6, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt

## Other (9 tables)
  Admin_User_Dtl | PK: Admin_User_Dtl_Id | Admin_User_Dtl_Id, User_Id, Business_System_id, Admin_User_From, Admin_User_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  Alert_Sender_Dtl | PK: Alert_Sender_Dtl_Id | Alert_Sender_Dtl_Id, Mail_Serv_Name, Mail_From_Address, Mail_User_Name, Mail_User_Password, Alert_Id, Cr_User_Id, Cr_Dt, ... (+2 more)
  Customer | PK: Id | Id, Name, Description
  EmployeeMaster | PK: None | Employee_Code, EMP_FNAME, EMP_MNAME, EMP_LNAME, Title, Gender, Date_Of_Birth, CompanyCode, ... (+12 more)
  Exchange_Rate_Mst | PK: None | Exchange_Rate_Freq, Currency_Id, Exchange_Rate_From, Exchange_Rate_To, Exchange_Rate, CR_USER_ID, CR_DT, MOD_USER_ID, ... (+1 more)
  SeperatedOil | PK: None | Company, Company Name, Department, Location, Title, Fname, Mname, Sname, ... (+11 more)
  SeperatedProjects | PK: None | Company, Company Name, Department, Location, Title, Fname, Mname, Sname, ... (+13 more)
  SeperatedSteel | PK: None | Company, Company Name, Department, Location, Title, Fname, Mname, Sname, ... (+12 more)
  django_migrations | PK: id | id, app, name, applied

## System (1 tables)
  System_Generic_Info | PK: None | System_Generic_Info_Id, System_Name, System_Abrv, Report_Dt_Caption, Automail_Footer, Group_Logo_Path, Cr_User_Id, Cr_Dt, ... (+2 more)

## User (4 tables)
  User_Access_Dtl | PK: None | User_Id, Access_Dt, Access_Type, Nr_User_Id
  User_Pwd_Reset_Dtl | PK: None | User_Id, Pwd_Reset_Dt, cr_dt
  User_Rights | PK: User_Rights_Id | User_Rights_Id, User_Id, Menu_Id, Right_Type, Right_From_Dt, CR_USER_ID, CR_DT
  User_Rights_Hst | PK: None | User_Rights_Id, User_Id, Menu_Id, Right_Type, Right_From_Dt, Right_To_Dt, CR_USER_ID, MOD_USER_ID, ... (+1 more)

## Vessel (1 tables)
  Vessel_Particulars | PK: None | Vessel_Id, Vessel_Info_Scan_Path, Speed_Per_Day_Loaded, Speed_Per_Day_Ballast, FO_Per_Day_Sea_Loaded, FO_Per_Day_Sea_Ballast, FO_Per_Day_Gear_Idle, FO_Per_Day_Gear_Working, ... (+9 more)

## Wkg (14 tables)
  Wkg_AD_Users | PK: None | ADsPath, Employee Code, First Name, Middle Name, Last Name, Alias Name, title, company, ... (+16 more)
  Wkg_Citrix_User_Dtl | PK: None | Employee_Code, User Name, Local_Access, Migrated_On, De_Migrated_On, Reason, Remark
  Wkg_Emp_LoginId_Info | PK: None | LoginId, Username, Employee_Code, Location
  Wkg_Hr_Org_Data | PK: None | Employee Code, Subhojit_Emp_SAP_Code, First name, Middle Name, Last name, Gender Key, CoCd, Company_Id, ... (+18 more)
  Wkg_IT_ApplnSupport_Excel | PK: None | emp_cd, emp_name
  Wkg_IT_Infra_Excel | PK: None | EMP_CD, Emp_FName, Emp_LName, Designation
  Wkg_IT_SW_License_Upload | PK: None | Company, ComputerUnique, LastknownIP, softwareName, Firstname, Lastname, SoftwarePublisher, softwareVersion, ... (+8 more)
  Wkg_Invoice | PK: None | done, Company_Id, Company, Vendor_Id, Vendor, Inv_no, Inv_date, Inv amt, ... (+6 more)
  Wkg_Kurla_Migration | PK: None | Sr#No, Employe Id, Exchange Alias, User Name, Company Name, Department, E- Mail Id, Mobile No, ... (+23 more)
  Wkg_Mahalaxmi_Migration | PK: None | Sr No, Emp Code, User Name, Domain Id, Ext, Mobile No, Company Name, Dept, ... (+9 more)
  Wkg_Mst_Co_Temp | PK: None | Co_code, Co_Name
  Wkg_Probable_Exit | PK: None | Emp_Code, Date_Of_Exit, Cr_Dt
  Wkg_SAP_HR_Emp_Data | PK: None | Company, Company Name, Department, Location, Title, Fname, Mname, Sname, ... (+13 more)
  Wkg_SAP_HR_Emp_Inactive_Data | PK: None | Emp_Code

## ebtsl (4 tables)
  ebtsl_Approval_Dtl | PK: Approval_Dtl_Id | Approval_Dtl_Id, Approval_By_Id, Invoice_Dtl_Id, Invoice_Received_On, Approval_Type, Remark, Cr_User_Id, Cr_Dt, ... (+2 more)
  ebtsl_Invoice_Dtl | PK: Invoice_Dtl_Id | Invoice_Dtl_Id, Invoice_No, Invoice_Dt, Financial_Year_Id, Invoice_Amt, Invoice_Balance_Amt, Vendor_Id, Dept_Id, ... (+7 more)
  ebtsl_Mst_Approval_By | PK: Approval_By_Id | Approval_By_Id, Approval_By_Name, Approval_Order, Approval_By_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  ebtsl_Mst_Vendor | PK: Vendor_Id | Vendor_Id, Vendor_Name, Vendor_Addr, Vendor_Tel, Vendor_Fax, Vendor_Email, Vendor_WebSite, Vendor_Contact_Person, ... (+5 more)

## eos (288 tables)
  eos_Activity_Monitor | PK: Activity_Monitor_Id | Activity_Monitor_Id, Activity_Id, Rig_Id, Activity_Monitor_Dt, Original_Monitor_Dt, Planning_Remark, Activity_Compl_Dt, Completion_Remark, ... (+5 more)
  eos_Actual_Crew_Expense | PK: None | Act_Crew_Expense_Id, Bud_Crew_Expense_Id, Fs_Emp_Id, Doc_No, Expense_Dt, Fs_Emp_Category_Id, Cost_Centre_Id, Rank_Id, ... (+10 more)
  eos_Ad_Hoc_Tr | PK: None | Ad_Hoc_Tr_Id, Fs_Emp_Id, Rank_Id, Emp_Type_Id, Fs_Category_Id, ED_Id, Tr_Dt, Rig_Id, ... (+11 more)
  eos_Appreciation_Letter | PK: None | App_Letter_Id, Fs_Emp_Id, Rank_Id, Rig_Id, App_Cert_Dt, App_Cert_No, Area_Of_Work, Reason_for_Award, ... (+5 more)
  eos_Approval_Code | PK: Approval_Code_Id | Approval_Code_Id, Approval_Code, Approval_Desc, Approval_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Approver_Mapping | PK: Approver_Mapping_Id | Approver_Mapping_Id, Approval_Code_Id, Approver_User_Id, Approver_Level, Approver_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Approver_Mapping_Dtl | PK: None | Approver_Mapping_Dtl_Id, Approver_Mapping_Id, Rig_Id, Dept_Id, Receive_Mail, Approve_YN, Open_For_Revision_YN, Create_YN, ... (+4 more)
  eos_BUPA_Insurance_Exceptions | PK: None | Ins_Exception_Id, Fs_Emp_Id, Payable, From_Dt, To_Dt, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_BUPA_Insurance_Payments | PK: None | Ins_Payment_Id, Ins_Payment_Dt, Fs_Emp_Id, Ins_Amt_Payable, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Budgeted_Crew_Expense | PK: Bud_Crew_Expense_Id | Bud_Crew_Expense_Id, Rig_Crew_Budget_Hdr_Id, Fs_Emp_Category_Id, Cost_Centre_Id, Rank_Id, Nationality, Crew_Expense_Id, Currency_Id, ... (+5 more)
  eos_Buss_Cert_Dtl | PK: Buss_Cert_Dtl_Id | Buss_Cert_Dtl_Id, Rig_Id, Buss_Cert_Id, Buss_Cert_No, Buss_Cert_Issue_Auth_Id, Buss_Cert_Dt, Buss_Cert_Valid_Till, Buss_Cert_Active, ... (+6 more)
  eos_Buss_Cert_Schedule_Dtl | PK: Buss_Cert_Schedule_Id | Buss_Cert_Schedule_Id, Buss_Cert_Dtl_Id, Buss_Cert_Schd_Dt, Buss_Cert_Schd_Type, Buss_Cert_Schd_Complete_Dt, Remarks, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Candidate_Experience_Dtl | PK: None | Candidate_Exp_Dtl_Id, Candidate_Interview_Hdr_Id, Exp_From_Dt, Exp_To_Dt, Exp_Years, Exp_Months, Company_Name, Designation, ... (+4 more)
  eos_Candidate_Interview_Competency | PK: None | Candidate_Interview_Comp_Id, Candidate_Interview_Hdr_Id, Dept_Id, Interviewer_Id, Competency_Id, Rating, Remarks, Cr_User_Id, ... (+3 more)
  eos_Candidate_Interview_Hdr | PK: Candidate_Interview_Hdr_Id | Candidate_Interview_Hdr_Id, Candidate_Fname, Candidate_Mname, Candidate_Lname, Present_Addr, Permanent_Addr, Father_Name, Nationality, ... (+23 more)
  eos_Candidate_Training_Dtl | PK: None | Candidate_Train_Dtl_Id, Candidate_Interview_Hdr_Id, Training_Type, Training_Agency, Training_Cert_No, Training_Cert_Dt, Cert_Valid_From_Dt, Cert_Valid_To_Dt, ... (+4 more)
  eos_Cert_To_Rank_Mapping | PK: None | Cert_To_Rank_Mapping_Id, Cert_Id, Fs_Category_Id, Rank_Id, Cert_To_Rank_Mapping_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Chcek_Full_Top_Section | PK: main_Sr_no | main_Sr_no, Rig_Id, SrNo, Location, First_Anchor_Down_Dt, Drilling_Completion_Dt, Cnt_Entry_12_1_4, Cnt_Entry_8_1_2
  eos_Company_Name_Change | PK: None | Company_Name_Change_Id, Company_Id, Company_Name, Company_Short_Name, Image_Path_Header, Image_Path_Footer, Image_Path_Stamp, From_Date, ... (+5 more)
  eos_Competitor_Contract_Dtl | PK: Competitor_Contract_Id | Competitor_Contract_Id, Competitor_Id, Rig_Name, Capacity_HP, Type_Of_Rig, Location, Contract_Status, Operator_Id, ... (+8 more)
  eos_Cost_Centre_To_Company_Mapping | PK: None | Comp_To_CC_Map_Id, Company_Id, Cost_Centre_Id, Mapping_From, Mapping_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Crew_Change_Reliever_Mapping | PK: None | CC_Reliever_Mapping_Id, Fs_Category_Id, Rank_Id, Reliever_Rank_Id, Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Crew_Group_Shift_Dtl | PK: Crew_Group_Shift_Dtl_Id | Crew_Group_Shift_Dtl_Id, Crew_Grp_Rotation_Id, Crew_Grp_Id, Rig_Id, Company_Id, Prj_Contract_Id, Crew_Grp_Shift, Crew_Grp_From, ... (+5 more)
  eos_Crew_Grp_Dtl | PK: None | Crew_Grp_Dtl_Id, Fs_Emp_Id, Rig_Id, Crew_Grp_Id, Crew_Grp_From, Crew_Grp_To, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Crew_Grp_Rotation | PK: None | Crew_Grp_Rotation_Id, Crew_Grp_Id, Relieving_Crew_Grp_Id, Crew_Grp_On_Dt, Crew_Grp_Off_Dt, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Crew_Insurance_Cover | PK: None | Insurance_Cover_Id, Fs_Emp_Id, Medical_Insurance_Cover, Accident_Insurance_Cover, Insurance_Cover_From, Insurance_Cover_To, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Crew_Insurance_Value | PK: None | Insurance_Value_Id, Fs_Category_Id, Crew_Level, Insured_Amt, Accident_Insurance_Cover, Insured_From_Dt, Insured_To_Dt, Cr_User_Id, ... (+3 more)
  eos_Crew_Schedule_Exceptions | PK: None | CS_Exception_Id, Fs_Category_Id, Emp_Type_Id, Rank_Id, Fs_Emp_Id, Exception_From, Exception_To, Cr_User_Id, ... (+3 more)
  eos_Crew_Travel_Dtl | PK: None | Crew_Travel_Dtl_Id, Crew_Travel_Req_Dt, Crew_Change_Dt, Crew_Travel_Dt, Travel_Info_Rig_Id, Rig_Id, Travel_Info_Crew_Id, Fs_New_Appl_Id, ... (+15 more)
  eos_Day_Rate_Form16 | PK: None | Day_Rate_Form16_Id, Emp_Name, PAN_No, Email_Id, Cr_User_Id, Cr_Dt
  eos_Day_Rate_Payslip | PK: None | Day_Rate_Payslip_Id, Fs_Emp_Id, Fs_Emp_Name, Nationality, Rank_Name, Fs_Emp_Email_Pers, Payroll_Month, Retainer_Day_Date_From, ... (+24 more)
  eos_Doc_To_Sign_Mapping | PK: None | Doc_To_Sign_Id, Doc_Name, Emp_Id, Sign_Path, Sign_From, Sign_To, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Drilling_Dtl | PK: Drilling_Dtl_Id | Drilling_Dtl_Id, Rig_Id, Drilling_Hdr_Id, Drilling_Dtl_Dt, POB_Operator, POB_Essar, POB_Essar_Serv, POB_Others, ... (+33 more)
  eos_Drilling_Dtl_Ops | PK: None | Drilling_Dtl_Ops_Id, Drilling_Dtl_Id, Time_From, Time_To, Work_Shift, Duration, Drilling_Ops_Id, Drilling_Section_Id, ... (+9 more)
  eos_Drilling_Hdr | PK: Drilling_Hdr_Id | Drilling_Hdr_Id, Prj_Contract_Id, Rig_Id, Latitude, Longitude, Location, Total_Water_Depth, Total_Depth, ... (+19 more)
  eos_Drilling_Work_Shift | PK: Drilling_Work_Shift_Id | Drilling_Work_Shift_Id, Prj_Contract_Id, Rig_Id, Work_Shift, Work_Shift_Start_Time, Work_Shift_End_Time, Work_Shift_Days, Work_Shift_Active, ... (+4 more)
  eos_Email_Notification_Letter | PK: EN_Letter_Id | EN_Letter_Id, Fs_Emp_Id, Rig_Id, Rank_Id, EN_Letter_Dt, EN_Type_Id, EN_Type_Subject, EN_Type_Description, ... (+5 more)
  eos_Email_Notification_Type | PK: EN_Type_Id | EN_Type_Id, EN_Type_Name, EN_Type_Subject, EN_Description, EN_Type_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Equip_Cert_Dtl | PK: None | Equip_Cert_Dtl_Id, Rig_Id, Equip_Id, Equip_Sub_Catg_Id, Equip_Cert_Party_Id, OEM, Equip_Cert_No, Equip_Cert_Dt, ... (+12 more)
  eos_Equip_Tech_Dtl | PK: None | Equip_Tech_Dtl_Id, Rig_Id, Pms_Grp3_Id, Tech_Dtl, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_External_POB_Dtl | PK: None | External_POB_Id, Person_Name, Rig_Serv_Provider_Id, Rig_Id, POB_From, POB_To, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Fs_Basic_Dtl | PK: Fs_Basic_Id | Fs_Basic_Id, Fs_Emp_Id, Rank_Id, Rank_To_Grade_Id, Fs_Category_Id, Emp_Type_Id, Basic_From, Basic_Amt, ... (+7 more)
  eos_Fs_CDC_Hst | PK: None | Fs_Emp_Id, CDC_No, CDC_Dt, CDC_Country_Id, CDC_place_Id, CDC_Valid_Till, Mod_User_Id, Mod_Dt
  eos_Fs_Catg_To_Rig_Type_Mapping | PK: None | Fs_Catg_To_Rig_Type_Mapping_Id, Fs_Category_Id, Rig_Type_Id, Mapping_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Fs_Certificates | PK: Fs_Certificate_Id | Fs_Certificate_Id, Fs_Emp_Id, Cert_Id, Cert_Level, Fs_Cert_No, Fs_Cert_Dt, Location_Id, Cert_Institute_Id, ... (+8 more)
  eos_Fs_Contract_Appendix_A_Dtl | PK: None | Appendix_A_Dtl_Id, Appendix_A_Hdr_Id, Appendix_A_Dtl_Description, Appendix_A_Dtl_Order, Appendix_A_Dtl_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Fs_Contract_Appendix_A_Hdr | PK: Appendix_A_Hdr_Id | Appendix_A_Hdr_Id, Fs_Category_Id, Category_Type, Rank_Id, Appendix_A_Hdr_Description, Appendix_A_Hdr_Order, Appendix_A_Hdr_Active, Cr_User_Id, ... (+3 more)
  eos_Fs_Contract_Dtl | PK: None | Fs_Contract_Dtl_Id, Fs_Contract_Hdr_Id, ED_Id, ED_Amt, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Fs_Contract_Hdr | PK: Fs_Contract_Hdr_Id | Fs_Contract_Hdr_Id, Company_Id, Proj_Company_Loc_Id, Reg_Company_Loc_Id, Fs_Emp_Id, Contract_Dt, Contract_From, Contract_To, ... (+20 more)
  eos_Fs_Emp_Bonus | PK: None | Fs_Emp_Bonus_Id, Bonus_Month, Fs_Emp_Id, Rank_Id, Rig_Id, Fs_Emp_Doj, Bonus_Effective_Dt, Period_From, ... (+7 more)
  eos_Fs_Emp_Correction | PK: None | Fs_Emp_Correction_Id, Entity_Name, Fs_Emp_Id, Fs_Relation_Id, Location_Id, Remarks, Old_Name, Corrected_Name, ... (+2 more)
  eos_Fs_Emp_Cur_Status | PK: Fs_Emp_Id | Fs_Emp_Id, Fs_Category_Id, Rank_Id, Emp_Type_Id, Serv_Type_Id, Serv_Subtype_Id, Serv_Subtype_From, Appx_End_Dt, ... (+8 more)
  eos_Fs_Emp_ED_Payable | PK: None | Fs_Emp_ED_Payable_Id, ED_Id, Rig_Id, Fs_Emp_Id, Month_Payable, ED_Payable, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Fs_Emp_Exit_Dtl | PK: Fs_Emp_Id | Fs_Emp_Id, Leaving_Reason_Id, Leaving_Reason_Dtl_Id, Cr_User_Id, Cr_Dt
  eos_Fs_Emp_Exit_Dtl_Log | PK: None | Fs_Emp_Id, Leaving_Reason_Id, Leaving_Reason_Dtl_Id, Del_User_Id, Del_Dt
  eos_Fs_Emp_FNFS_Letter_Tmp | PK: None | Fs_Emp_Id, Fs_Emp_Staff_Id, Serv_Subtype_From, Serv_Subtype_To, Total_ON_Days, ON_Days_Payable_Jun, OFF_Duty_Paid_Days_Apr, OFF_Duty_Paid_Days_May, ... (+21 more)
  eos_Fs_Emp_Follow_Up_Dtl | PK: None | Fs_Emp_Follow_Up_Id, Fs_Emp_Id, Follow_Up_Dt, Follow_Up_Remarks, View_Type, Follow_Up_Status, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Fs_Emp_Hiring | PK: None | Fs_New_Appl_Id, Fs_Emp_Doj, Company_Id, Company, Department, HR_Admin, Time_Admin, Payroll_Admin, ... (+12 more)
  eos_Fs_Emp_Medical_Checkup | PK: None | Medical_Checkup_Id, Fs_New_Appl_Id, Fs_Emp_Id, Medical_Centre_Name, Scheduled_Test_Dt, Actual_Test_Dt, Status, Medical_Cert_No, ... (+7 more)
  eos_Fs_Emp_Profile_Dtl | PK: None | Emp_Profile_Id, Fs_Emp_Id, Profile_Verification_Dt, Cr_User_Id, Cr_Dt
  eos_Fs_Emp_Promotion | PK: None | Fs_Emp_Promotion_Id, Entity_Name, Fs_Emp_Id, Location_Id, Previous_Level, New_Level, New_Sum_Insured, Upgrade_Dt, ... (+2 more)
  eos_Fs_Emp_Remark_Dtl | PK: Fs_Emp_Rem_Id | Fs_Emp_Rem_Id, Fs_Emp_Id, Rank_Id, Remark_Dt, Remark, Remark_Type, View_Type, Email_Alert_Dt, ... (+4 more)
  eos_Fs_Emp_To_CC_Mapping | PK: None | Fs_Emp_To_CC_Map_Id, Cost_Centre_Id, Fs_Emp_Id, Mapping_From, Mapping_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Fs_Inactive_Dtl | PK: None | Fs_Inactive_Id, Fs_Emp_Id, Inactive_From, Remark, Inactive_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Fs_Interview_Dtl | PK: None | Fs_Interview_Dtl_Id, Fs_Interview_Hdr_Id, Fs_Interview_Dtl_Dt, Emp_Id, Interview_Dtl_Status, Remarks, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Fs_Interview_Hdr | PK: Fs_Interview_Hdr_Id | Fs_Interview_Hdr_Id, Fs_Interview_Schd_Dt, Fs_New_Appl_Id, Rank_Id, Fs_Interview_Hdr_Status, Fs_Interview_Form_Path, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Fs_New_Appl_Certificates | PK: None | Fs_New_Appl_Certificate_Id, Fs_New_Appl_Id, Cert_Id, Cert_Level, Fs_Cert_No, Fs_Cert_Dt, Location_Id, Cert_Institute_Id, ... (+8 more)
  eos_Fs_New_Appl_Dtl | PK: Fs_New_Appl_Id | Fs_New_Appl_Id, Fs_New_Appl_No, Fs_New_Appl_Dt, Fs_Emp_Fname, Fs_Emp_Mname, Fs_Emp_Lname, Permanent_Addr, Mailing_Addr, ... (+42 more)
  eos_Fs_New_Appl_Dtl_Temp | PK: None | Fs_New_Appl_Id, Fs_New_Appl_No, Fs_New_Appl_Dt, Fs_Emp_Fname, Fs_Emp_Mname, Fs_Emp_Lname, Permanent_Addr, Mailing_Addr, ... (+31 more)
  eos_Fs_New_Followup_Dtl | PK: Fs_New_Followup_Id | Fs_New_Followup_Id, Fs_New_Appl_Id, Followup_Dt, Remark, Email_Alert_Dt, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Fs_New_Prv_Rig_Ex | PK: Fs_New_Prv_Rig_Ex_Id | Fs_New_Prv_Rig_Ex_Id, Fs_New_Appl_Id, Rig_Company_Name, Rank_Id, Rig_Id, Rig_Name, Rig_Subtype_Id, Rig_Location, ... (+10 more)
  eos_Fs_Offer_Letter | PK: None | Fs_New_Appl_Id, Fs_Offer_Letter_Dt, Rank_Id, Rank_To_Grade_Id, Rig_Site_Mapping_Id, Contact_Person, Contact_Tel_No, Fs_Offer_Letter_DOJ, ... (+40 more)
  eos_Fs_Official_Info | PK: Fs_Emp_Id | Fs_Emp_Id, PAN, VPF_Rate, Bank_Id_1, Bank_Name_1, Bank_Br_Id_1, Bank_Br_Name_1, Swift_Id_1, ... (+22 more)
  eos_Fs_Other_Dtl | PK: Fs_Emp_Id | Fs_Emp_Id, Boiler_Suit_Size, Safety_Shoes_Size, Cr_User_Id, Cr_Dt
  eos_Fs_PP_CDC_Scan | PK: Fs_Emp_Id | Fs_Emp_Id, Fs_pp_Scan_Path, Fs_cdc_Scan_Path, Mod_User_Id, Mod_Dt
  eos_Fs_PP_Hst | PK: None | Fs_Emp_Id, PP_No, PP_Dt, PP_Country_Id, PP_Place_Id, PP_Valid_Till, PP_Ecnr, Mod_User_Id, ... (+1 more)
  eos_Fs_Prv_Rig_Ex | PK: Prv_Rig_Ex_Id | Prv_Rig_Ex_Id, Fs_Emp_Id, Rig_Company_Name, Rank_Id, Rig_Id, Rig_Name, Rig_Subtype_Id, Rig_Location, ... (+10 more)
  eos_Fs_Prv_Rig_Ex_Tender | PK: Prv_Rig_Ex_Tender_Id | Prv_Rig_Ex_Tender_Id, Prv_Rig_Ex_Id, Fs_Emp_Id, Rig_Company_Name, Rank_Id, Rig_Id, Rig_Name, Rig_Subtype_Id, ... (+11 more)
  eos_Fs_Qualification | PK: None | Fs_Qualification_Id, Fs_Emp_Id, Qualification_Id, Completion_Year, Institute_Name, Location_Id, Remarks, Marks_Obtained, ... (+4 more)
  eos_Fs_Relation_Dtl | PK: Fs_Relation_Id | Fs_Relation_Id, Fs_Emp_Id, Fs_Relation_Name, Relation_Id, Gender, Fs_Rel_DOB, Fs_Rel_POB, Fs_Rel_Country_Id, ... (+10 more)
  eos_Fs_Shift_Dtl | PK: None | Fs_Shift_Dtl_Id, Rig_Id, Fs_Emp_Id, Crew_Shift, Shift_From, Shift_To, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Fs_Visa | PK: Fs_Visa_Id | Fs_Visa_Id, Fs_Emp_Id, Country_Id, Fs_Visa_No, Fs_Visa_Dt, Fs_Visa_Valid_Till, Location_Id, CR_USER_ID, ... (+3 more)
  eos_GRN_Dtl | PK: GRN_Dtl_Id | GRN_Dtl_Id, GRN_Hdr_Id, MR_Dtl_Id, SR_Dtl_Id, SAP_No, Equip_Make_Id, Equip_Model_Id, Equip_Part_Id, ... (+14 more)
  eos_GRN_Hdr | PK: Grn_Hdr_Id | Grn_Hdr_Id, Grn_No, Grn_Dt, Location, Vendor_Id, Receipt_Dt, Requisition_Type, MR_Hdr_Id, ... (+21 more)
  eos_GST_Details | PK: None | GST_Dtl_Id, Company_Id, Country_State_Id, GST_Number, GST_Reg_Address, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_HSE_Drill_Record_Corrective_Action | PK: None | Drill_Rec_Corrective_Action_Id, Drill_Record_Hdr_Id, Drill_Rec_Corrective_Action_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_HSE_Drill_Record_Event | PK: None | Drill_Rec_Event_Id, Drill_Record_Hdr_Id, Drill_Rec_Event_Time, Drill_Rec_Event_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_HSE_Drill_Record_Hdr | PK: Drill_Record_Hdr_Id | Drill_Record_Hdr_Id, Rig_Id, Drill_Record_Sr_No, Drill_Record_No, Drill_Dt, Drill_Location, HSE_Drill_Id_1, HSE_Drill_Id_2, ... (+24 more)
  eos_HSE_Drill_Record_Improvement | PK: None | Drill_Rec_Improvement_Id, Drill_Record_Hdr_Id, Drill_Rec_Improvement_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_HSE_Drill_Record_Observation | PK: None | Drill_Rec_Observation_Id, Drill_Record_Hdr_Id, Drill_Rec_Observation_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_HSE_Drill_Record_Photo_Upload | PK: None | Drill_Rec_Photo_Upload_Id, Drill_Record_Hdr_Id, Drill_Rec_Photo_Upload_Path, Drill_Rec_Photo_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_HSE_Training_Group_Dtl | PK: None | Training_Group_Dtl_Id, Training_Group_Hdr_Id, Fs_Category_Id, Rank_Id, Mandatory_Training, Training_Group_Dtl_Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_HSE_Training_Group_Hdr | PK: Training_Group_Hdr_Id | Training_Group_Hdr_Id, Training_Group_Hdr_Name, Training_Group_Hdr_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_HSE_Training_Log_Dtl | PK: None | Training_Log_Dtl_Id, Training_Log_Hdr_Id, Training_Party, Fs_Emp_Id, Trainee_Fname, Trainee_Mname, Trainee_Lname, Fs_Category_Id, ... (+12 more)
  eos_HSE_Training_Log_Hdr | PK: Training_Log_Hdr_Id | Training_Log_Hdr_Id, Rig_Id, Cert_Id, Training_Location, Training_Dt, Training_Type, Course_Duration, Training_Org_Hdr_Id, ... (+6 more)
  eos_HSE_Training_Org_Dtl | PK: Training_Org_Dtl_Id | Training_Org_Dtl_Id, Training_Org_Hdr_Id, Trainer_Fname, Trainer_Mname, Trainer_Lname, Trainer_Qualification, Trainer_Mobile_No, Trainer_Email_Id, ... (+4 more)
  eos_HSE_Training_Org_Hdr | PK: Training_Org_Hdr_Id | Training_Org_Hdr_Id, Training_Org_Name, Training_Org_Address, Location_Id, Country_Id, Contact_Person_1, Tel_No_1, Contact_Person_2, ... (+6 more)
  eos_HSE_Weekly_Drill_Dtl | PK: None | HSE_Weekly_Drill_Dtl_Id, HSE_Weekly_Drill_Hdr_Id, HSE_Drill_Id, Drill_Conducted_Dt, Drill_Last_Conducted_Dt, Remarks, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_HSE_Weekly_Drill_Hdr | PK: HSE_Weekly_Drill_Hdr_Id | HSE_Weekly_Drill_Hdr_Id, Rig_Id, Drill_Year, Drill_Week, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_HS_Dashboard_To_User_Mapping | PK: None | HSD_To_User_Mapping_Id, HS_Dashboard_Id, User_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Hazard_ID_Card | PK: Haz_Card_Id | Haz_Card_Id, Haz_ID_Card_No, Prj_Contract_Id, Rig_Id, Event_Dt, Reported_By_Party, Reported_By_Fs_Emp_Id, Reported_By_Name, ... (+17 more)
  eos_Hazard_ID_Card_Client | PK: Haz_Card_Id | Haz_Card_Id, Haz_ID_Card_No, Prj_Contract_Id, Rig_Id, Event_Dt, Reported_By_Party, Reported_By_Fs_Emp_Id, Reported_By_Name, ... (+17 more)
  eos_Hitch_Adjustment | PK: None | Hitch_Adj_Id, Rig_Id, Tr_Dt, Fs_Emp_Id, Rank_Id, Emp_Type_Id, Fs_Category_Id, Adj_From_Dt, ... (+6 more)
  eos_Hitch_Not_Payable | PK: Serv_Dtl_Id | Serv_Dtl_Id, Hitch_Payable, Future_Hitch_Payable, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Incident_Actions | PK: None | Incident_Action_Id, Incident_Id, Action_Recommended, Action_Taken, Action_Party, Target_Date, Completion_Dt, Action_Status, ... (+6 more)
  eos_Incident_Actions_Hist | PK: None | Incident_Action_Id, Incident_Id, Action_Recommended, Action_Taken, Action_Party, Target_Date, Completion_Dt, Action_Status, ... (+4 more)
  eos_Incident_Details | PK: Incident_Id | Incident_Id, Work_Location_Id, Rig_Id, Unit_Name, Rig_Incident_No, Incident_No, Incident_Date, Financial_Year_Id, ... (+46 more)
  eos_Incident_Details_Hist | PK: None | Incident_Id, Work_Location_Id, Rig_Id, Unit_Name, Rig_Incident_No, Incident_No, Incident_Date, Financial_Year_Id, ... (+43 more)
  eos_Incident_Photos | PK: None | Incident_Photo_Id, Incident_Id, Incident_Photo_Path, Incident_Photo_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Incident_Photos_Hist | PK: None | Incident_Photo_Id, Incident_Id, Incident_Photo_Path, Incident_Photo_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Incident_Root_Cause | PK: None | Incident_Root_Cause_Id, Incident_Id, Root_Cause_Id, Root_Subcause_Id, Root_Subcause_Others, Marked_As_Deleted, Deleted_Remarks, Cr_User_Id, ... (+3 more)
  eos_Invoice_Dtl | PK: None | Invoice_Dtl_Id, Invoice_Hdr_Id, SAP_No, Item_Desc, HSN_SAC, UOM_ID, Qty, Rate, ... (+6 more)
  eos_Invoice_Hdr | PK: Invoice_Hdr_Id | Invoice_Hdr_Id, Cost_Centre_Id, Prj_Contract_Id, Invoice_Type, Invoice_No, Invoice_Dt, Invoice_Amt, Invoice_Month, ... (+50 more)
  eos_Invoice_Monitoring_Log | PK: None | Inv_Monitoring_Log_Id, Invoice_Hdr_Id, Log_Entry_Dt, Log_Entry_Value, Log_Action, User_Id, Approver_Level, Remarks
  eos_Job_Description_Dtl | PK: None | JD_Dtl_Id, JD_Hdr_Id, JD_Dtl_Description, JD_Dtl_Order, JD_Dtl_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Job_Description_Hdr | PK: JD_Hdr_Id | JD_Hdr_Id, Fs_Category_Id, Rank_Id, JD_Hdr_Description, JD_Hdr_Order, JD_Hdr_Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Lagging_Indicators_Dtl | PK: None | Lagging_Indicator_Dtl_Id, Lagging_Indicator_Id, Workgroup_Id, Indicator_Type_Id, Indicator_Subtype_Id, Total_Count, Active, Cr_User_Id, ... (+3 more)
  eos_Lagging_Indicators_Hdr | PK: Lagging_Indicator_Id | Lagging_Indicator_Id, Company_Id, Rig_Id, Report_No, Period, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Leading_Indicators_Dtl | PK: None | Leading_Indicator_Dtl_Id, Leading_Indicator_Id, Workgroup_Id, Indicator_Type_Id, Indicator_Subtype_Id, Total_Sessions, No_Of_Persons, Total_Duration, ... (+6 more)
  eos_Leading_Indicators_Hdr | PK: Leading_Indicator_Id | Leading_Indicator_Id, Company_Id, Rig_Id, Report_No, Period, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Lock_Transaction_Date | PK: None | Lock_Transaction_Date_Id, Fs_Category_Id, Lock_Transaction_Day, Active, Mod_User_Id, Mod_Dt
  eos_Lock_Transaction_Dtl | PK: None | Lock_Transaction_Dtl_Id, Lock_Transaction_Hdr_Id, Lock_Type, Remarks, Mod_User_Id, Mod_Dt
  eos_Lock_Transaction_Hdr | PK: Lock_Transaction_Hdr_Id | Lock_Transaction_Hdr_Id, Fs_Category_Id, Lock_Transaction_Month, Lock_Transaction_YN, Remarks, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Lock_Transaction_Temp | PK: Lock_Transaction_Hdr_Id | Lock_Transaction_Hdr_Id, Fs_Category_Id, Lock_Transaction_Month, Lock_Transaction_YN, Remarks, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Lock_Transaction_Temp_Dtl | PK: None | Lock_Transaction_Dtl_Id, Lock_Transaction_Hdr_Id, Lock_Type, Remarks, Mod_User_Id, Mod_Dt
  eos_MIS_Monthly_HSE_Activities | PK: None | Monthly_HSE_Activity_Id, Monthly_HSE_Returns_Hdr_Id, HSE_Activity_Id, Total_Activities, Eosil_Emp_Count, Contractor_Count, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_MIS_Monthly_HSE_Cards | PK: None | Monthly_HSE_Card_Id, Monthly_HSE_Returns_Hdr_Id, Card_Type, Eosil_Open_Cards, Eosil_Closed_Cards, Contractors_Open_Cards, Contractors_Closed_Cards, Cr_User_Id, ... (+3 more)
  eos_MIS_Monthly_HSE_Environment | PK: None | Monthly_HSE_Environment_Id, Monthly_HSE_Returns_Hdr_Id, HSE_Consumable_Id, Total_Quantity, Remarks, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_MIS_Monthly_HSE_Incidents | PK: None | Monthly_HSE_Incident_Id, Monthly_HSE_Returns_Hdr_Id, Incident_Type_Id, Eosil_Total_Incidents, Contractor_Total_Incidents, LTI_Free_Days, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_MIS_Monthly_HSE_Manhours | PK: None | Monthly_HSE_Manhours_Id, Monthly_HSE_Returns_Hdr_Id, HSE_Manhours_Party_Id, No_Of_Personnel, Hours_Worked, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_MIS_Monthly_HSE_Meetings | PK: None | Monthly_HSE_Meeting_Id, Monthly_HSE_Returns_Hdr_Id, HSE_Meeting_Id, Total_Meetings, Total_Eosil_Employees, Total_Contractors, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_MIS_Monthly_HSE_Returns_Hdr | PK: Monthly_HSE_Returns_Hdr_Id | Monthly_HSE_Returns_Hdr_Id, Cost_Centre_Id, Rig_Id, Report_No, Report_Month, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_MIS_Monthly_HSE_Vehicle_Info | PK: None | Monthly_HSE_Vehicle_Id, Monthly_HSE_Returns_Hdr_Id, Vehicle_No, Vehicle_Type, KM_Driven, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_MNT_Checklist_Dtl | PK: None | MNT_Checklist_Dtl_Id, MNT_Checklist_Hdr_Id, MNT_Category_Id, MNT_Sub_Category_Id, Task_Completed, Remarks, Fail_Category, Cr_User_Id, ... (+3 more)
  eos_MNT_Checklist_Hdr | PK: MNT_Checklist_Hdr_Id | MNT_Checklist_Hdr_Id, MNT_Checklist_Template_Hdr_Id, Checklist_Subject, WI_No, Checklist_Dt, Controlled_By, Prepared_By, Reviewed_By, ... (+7 more)
  eos_MNT_Checklist_Template_Dtl | PK: None | MNT_Checklist_Template_Dtl_Id, MNT_Checklist_Template_Hdr_Id, MNT_Category_Id, Display_Order, Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_MNT_Checklist_Template_Hdr | PK: MNT_Checklist_Template_Hdr_Id | MNT_Checklist_Template_Hdr_Id, Rig_Id, Dept_Id, MNT_Checklist_Template_Name, MNT_Checklist_Template_Type, Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_MR_Part_To_Desc_Mapping | PK: None | Part_To_Desc_Mapping_Id, Part_No, Material_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Manpower_Approval | PK: None | Manpower_Approval_Id, Prj_Contract_Id, Rig_Id, Fs_Emp_Id, Rank_Id, Doc_Submitted, Doc_Submitted_Dt, Client_Approval_Dt, ... (+5 more)
  eos_Material_Requisition_Dtl | PK: MR_Dtl_Id | MR_Dtl_Id, MR_Hdr_Id, SAP_No, Equip_Make_Id, Equip_Model_Id, Equip_Part_Id, UOM_Id, Qty, ... (+9 more)
  eos_Material_Requisition_Hdr | PK: MR_Hdr_Id | MR_Hdr_Id, Prj_Contract_Id, Rig_id, MR_No, MR_Dt, Dept_Id, Priority, MR_Type, ... (+27 more)
  eos_Mobile_Bill_Dtl | PK: None | Mobile_Bill_Dtl_Id, Mobile_Bill_Hdr_Id, Mobile_No_Id, Monthly_Charges, Call_Charges, Internet_Data_Charges, Roaming_Charges, Other_Charges, ... (+7 more)
  eos_Mobile_Bill_Hdr | PK: Mobile_Bill_Hdr_Id | Mobile_Bill_Hdr_Id, Vendor_Id, Location_Id, Bill_No, Bill_Dt, Bill_Amt, Calc_Bill_Amt, Bill_Amt_Tally, ... (+8 more)
  eos_Mobile_Holder | PK: None | Mobile_Holder_Id, Mobile_No_Id, Holder_Type, Fs_Emp_Id, Emp_Id, NonEmp_Id, Holder_Name, Cost_Centre_Id, ... (+7 more)
  eos_Monthly_POB_Summary | PK: None | Monthly_POB_Id, Rig_Id, POB_Month, POB_Manhours_EOSIL, POB_Manhours_TP, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_Associated_Crew_Expense | PK: Crew_Expense_Id | Crew_Expense_Id, Crew_Expense_Head, Crew_Expense_Desc, Crew_Expense_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Cert_Institute | PK: Cert_Institute_Id | Cert_Institute_Id, Cert_Institute_Name, Cert_Institute_Shortname, Cert_Institute_Address, Location_Id, Tel_No, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Mst_Client | PK: Client_Id | Client_Id, Client_Name, Client_Short_Name, Client_SAP_Code, WBS_Client_Code, Location_Id, Country_Id, Contact_Person, ... (+7 more)
  eos_Mst_Competency | PK: Competency_Id | Competency_Id, Competency_Name, Dept_Id, Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Competitor | PK: Competitor_Id | Competitor_Id, Competitor_Name, Cr_User_Id, Cr_Dt
  eos_Mst_Contact_Exposure_Type | PK: Contact_Expo_Type_Id | Contact_Expo_Type_Id, Contact_Expo_Type_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Contractor | PK: Contractor_Id | Contractor_Id, Contractor_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Cost_Centre | PK: Cost_Centre_Id | Cost_Centre_Id, Cost_Centre_Type_Id, Cost_Centre_Name, Old_Cost_Centre_Name, Rig_Id, Fs_Emp_Id, Location_Id, Cost_Centre_Active, ... (+4 more)
  eos_Mst_Cost_Centre_Type | PK: Cost_Centre_Type_Id | Cost_Centre_Type_Id, Cost_Centre_Type_Name, Cost_Centre_Type_Shortname, Cost_Centre_Type_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Crew_Grp | PK: Crew_Grp_Id | Crew_Grp_Id, Crew_Grp_Name, Rig_Id, Hitch, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Drilling_Operations | PK: Drilling_Ops_Id | Drilling_Ops_Id, Drilling_Ops_Code_No, Drilling_Ops_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Drilling_Rate | PK: Drilling_Rate_Id | Drilling_Rate_Id, Rate_Code, Rate_Description, Rate_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Drilling_Section | PK: Drilling_Section_Id | Drilling_Section_Id, Drilling_Section_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_ED | PK: ED_Id | ED_Id, ED_Type_Id, ED_Name, ED_Abrv, Pattern, Taxable, Perquisite, Serv_Dtl_DpnDt, ... (+10 more)
  eos_Mst_ED_To_Formula_Dtl | PK: ED_To_Formula_Dtl_Id | ED_To_Formula_Dtl_Id, ED_To_Formula_Id, Dependent_ED_Id, Dependent_ED_Percent, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_ED_To_Formula_Hdr | PK: ED_To_Formula_Id | ED_To_Formula_Id, Rank_Id, Emp_Type_Id, Serv_Type_Id, Serv_Subtype_Id, ED_Id, Percent_For_Calc, Payment_Frequency, ... (+6 more)
  eos_Mst_ED_Value | PK: ED_Value_Id | ED_Value_Id, Rank_Id, Emp_Type_Id, ED_Id, Serv_Type_Id, Serv_Subtype_Id, Percent_Of_Basic, Percent_Of_CTC, ... (+8 more)
  eos_Mst_Equip_Cert_Party | PK: Equip_Cert_Party_Id | Equip_Cert_Party_Id, Equip_Cert_Party_Name, Equip_Cert_Party_Shortname, Equip_Cert_Party_Address, Location_Id, Tel_No, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Mst_Equip_Certificate | PK: Equip_Cert_Id | Equip_Cert_Id, Equip_Cert_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Equip_Sub_Category | PK: Equip_Sub_Catg_Id | Equip_Sub_Catg_Id, Equip_Id, Equip_Sub_Catg_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Equip_Sub_Catg_Desc | PK: Equip_Sub_Catg_Desc_Id | Equip_Sub_Catg_Desc_Id, Equip_Sub_Catg_Id, Equip_Sub_Catg_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Equipment | PK: Equip_Id | Equip_Id, Equip_Group_Id, Equip_TA_No, Equip_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Equipment_Group | PK: Equip_Group_Id | Equip_Group_Id, Equip_Group_TA_No, Equip_Group_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Equipment_Make | PK: Equip_Make_Id | Equip_Make_Id, Equip_Make_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Equipment_Model | PK: Equip_Model_Id | Equip_Model_Id, Equip_Model_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Equipment_Part | PK: Equip_Part_Id | Equip_Part_Id, Equip_Make_Id, Equip_Model_Id, Equip_Part_No, Equip_Part_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_Expense_Type | PK: Expense_Type_Id | Expense_Type_Id, Expense_Type, Expense_Type_Desc, PO_Doc_Type_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Fs_Emp_ED_Value | PK: Fs_Emp_ED_Value_Id | Fs_Emp_ED_Value_Id, Fs_Emp_Id, ED_Id, Serv_Type_Id, Serv_Subtype_Id, Trn_Type, Percent_Of_Basic, ED_Amt, ... (+11 more)
  eos_Mst_Fs_Employee | PK: Fs_Emp_Id | Fs_Emp_Id, Fs_Emp_Fname, Fs_Emp_Mname, Fs_Emp_Lname, Permanent_Addr, Mailing_Addr, Emergency_Addr, Fs_Emp_Tel_No, ... (+55 more)
  eos_Mst_Fs_Kin_Dtl | PK: Fs_Kin_Id | Fs_Kin_Id, Fs_Emp_Id, Fs_Kin_Name, Relation_id, Fs_Kin_Addr, Fs_Kin_Tele, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Mst_Grade | PK: Grade_Id | Grade_Id, Grade_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_HSE_Activity | PK: HSE_Activity_Id | HSE_Activity_Id, HSE_Activity_Name, HSE_Activity_Type, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_HSE_Consumable | PK: HSE_Consumable_Id | HSE_Consumable_Id, HSE_Consumable_Name, HSE_Consumption_Unit, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_HSE_Drill | PK: HSE_Drill_Id | HSE_Drill_Id, HSE_Drill_Name, HSE_Drill_Frequency, Rig_Type_Id, HSE_Drill_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_HSE_Manhours_Party | PK: HSE_Manhours_Party_Id | HSE_Manhours_Party_Id, HSE_Manhours_Party_Name, HSE_Manhours_Party_Type, Cost_Centre_Type_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_HSE_Meeting | PK: HSE_Meeting_Id | HSE_Meeting_Id, HSE_Meeting_Type, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Hazard_Type | PK: Haz_Type_Id | Haz_Type_Id, Haz_Type_Name, Haz_Type_Class, Haz_Type_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Home_Screen_Dashboard | PK: HS_Dashboard_Id | HS_Dashboard_Id, HS_Dashboard_Name, HS_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Indicator_Subtype | PK: Indicator_Subtype_Id | Indicator_Subtype_Id, Indicator_Type_Id, Indicator_Subtype_Name, Indicator_Subtype_Order, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Indicator_Type | PK: Indicator_Type_Id | Indicator_Type_Id, Indicator_Type_Name, Indicator_Type_Order, Report_Type, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Interviewer | PK: Interviewer_Id | Interviewer_Id, User_Id, Dept_Id, Sign_Path, Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_MNT_Category | PK: MNT_Category_Id | MNT_Category_Id, MNT_Category_Name, Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_MNT_Sub_Category | PK: MNT_Sub_Category_Id | MNT_Sub_Category_Id, MNT_Category_Id, MNT_Sub_Category_Name, Sub_Catg_Display_Order, Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_Mobile_Nos | PK: Mobile_No_Id | Mobile_No_Id, Mobile_No, Account_No, Vendor_Id, Device_Type, Mobile_Plan, SIM_ICCID_No, MAC_Id, ... (+8 more)
  eos_Mst_OPC_Category | PK: OPC_Category_Id | OPC_Category_Id, OPC_Category_Name, OPC_Category_Shortname, OPC_Category_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Operator | PK: Operator_Id | Operator_Id, Operator_Name, Operator_Short_Name, Operator_SAP_Code, WBS_Client_Code, Location_Id, Country_Id, Contact_Person, ... (+7 more)
  eos_Mst_PO_Document_Type | PK: PO_Doc_Type_Id | PO_Doc_Type_Id, PO_Doc_Type_Name, PO_Doc_Type_Desc, Expense_Group, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Parts_Of_Body | PK: Part_Of_Body_Id | Part_Of_Body_Id, Part_Of_Body_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Plant | PK: Plant_Code | Plant_Code, Location_Id, Company_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Pms_Grp1 | PK: Pms_Grp1_Id | Pms_Grp1_Id, Pms_Grp1_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Pms_Grp2 | PK: Pms_Grp2_Id | Pms_Grp2_Id, Pms_Grp2_Name, Pms_Grp1_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Pms_Grp3 | PK: Pms_Grp3_Id | Pms_Grp3_Id, Pms_Grp3_Name, Pms_Grp2_Id, Pms_Grp1_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Project | PK: Project_Id | Project_Id, Plant_Code, Location_Id, Operator_Id, Start_Dt, End_Dt, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Mst_Project_Contract | PK: Prj_Contract_Id | Prj_Contract_Id, Location_Id, Operator_Id, Prj_Contract_No, Prj_Short_Name, Prj_Start_Dt, Prj_End_Dt, Cr_User_Id, ... (+3 more)
  eos_Mst_Project_Contract_Dtl | PK: None | Prj_Contract_Dtl_Id, Prj_Contract_Id, Rig_Id, Rig_Active_From, Rig_Active_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_Purchase_Group | PK: Purchase_Group_Id | Purchase_Group_Id, Purchase_Group_Code, Purchase_Group_Desc, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_QHSE_Category | PK: QHSE_Category_Id | QHSE_Category_Id, QHSE_Category_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Rig | PK: Rig_Id | Rig_Id, Rig_Name, Rig_Short_Name, Old_Rig_Name, Rig_Subtype_Id, Rig_Type_Id, Rig_Built_Dt, Rig_Tel_No, ... (+11 more)
  eos_Mst_Rig_Operation | PK: Rig_Operation_Id | Rig_Operation_Id, Rig_Operation_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Rig_Service_Provider | PK: Rig_Serv_Provider_Id | Rig_Serv_Provider_Id, Rig_Serv_Provider_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Sal_Exchange_Rate | PK: None | Exchange_Rate_Id, Currency_Id, Exchange_Rate_From, Exchange_Rate_To, Exchange_Rate, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_UOM | PK: UOM_Id | UOM_Id, UOM_Name, UOM_Short_Name, UOM_SAP_Code, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_User_Fs_Catg_Mapping | PK: None | User_Fs_Catg_Mapping_Id, User_Id, Fs_Category_Id, User_Fs_Catg_Mapping_From, User_Fs_Catg_Mapping_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_User_Rig_Mapping | PK: None | User_Rig_Mapping_Id, User_Id, Rig_Id, User_Rig_Mapping_From, User_Rig_Mapping_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Mst_Vehicle | PK: Vehicle_Id | Vehicle_Id, Vendor_Id, Vehicle_Type_Id, Vehicle_Subtype_Id, Vehicle_No, Vehicle_Make_Id, Vehicle_Model_Id, Engine_No, ... (+15 more)
  eos_Mst_Vehicle_Make | PK: Vehicle_Make_Id | Vehicle_Make_Id, Vehicle_Make_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Vehicle_Model | PK: Vehicle_Model_Id | Vehicle_Model_Id, Vehicle_Model_Name, Vehicle_Make_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mst_Workgroup | PK: Workgroup_Id | Workgroup_Id, Workgroup_Name, Workgroup_Order, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Mutual_Understanding | PK: MU_Id | MU_Id, Rig_Id, Out_Fs_Emp_Id, Out_Serv_Type_Id, Out_Serv_Subtype_Id, Out_From_Dt, Out_To_Dt, In_Fs_Emp_Id, ... (+16 more)
  eos_Nationality_To_Emp_Type_Mapping | PK: None | Nat_To_Emp_Type_Map_Id, Fs_Category_Id, Nationality, Emp_Type_Id, Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_OPC_HSD_Expense | PK: None | HSD_Expense_ID, Cost_Centre_Id, Expense_Month, Sr_No, Issue_Dt, Item_Desc, UOM, Currency_Id, ... (+9 more)
  eos_OPC_Manpower_Expense | PK: None | Manpower_Expense_Id, Cost_Centre_Id, Expense_Month, Sr_No, Manpower_Expense_Dt, Manpower_Expense_Desc, Currency_Id, Qty, ... (+9 more)
  eos_OPC_Material_Cost | PK: None | Material_Cost_Id, Cost_Centre_Id, Expense_Month, Dept_Id, OPC_Category_Id, GRN_Dtl_Id, MIN_No, Sr_No, ... (+20 more)
  eos_OPC_Project_Office_Exp | PK: None | Prj_Office_Exp_Id, Cost_Centre_Id, Expense_Month, Prj_Office_Exp_Dt, Sr_No, Reg_No, Prj_Office_Exp_Desc, Currency_Id, ... (+9 more)
  eos_OPC_Rig_Imprest | PK: None | Rig_Imprest_Id, Cost_Centre_Id, Expense_Month, Statement_No, Opening_Bal, Sr_No, Trn_Dt, Voucher_No, ... (+14 more)
  eos_OPC_Service_Expense | PK: None | Service_Expense_ID, Cost_Centre_Id, Expense_Month, Sr_No, Vendor, Item_Desc, UOM, Currency_Id, ... (+9 more)
  eos_OPC_TP_Hire | PK: None | TP_Hire_Id, Cost_Centre_Id, Expense_Month, TP_Hire_Dt, Sr_No, Reg_No, Hire_Desc, Currency_Id, ... (+9 more)
  eos_OPC_Training_Expense | PK: None | Training_Expense_Id, Cost_Centre_Id, Expense_Month, Sr_No, Training_Expense_Dt, Training_Agency_Name, Training_Expense_Desc, Currency_Id, ... (+6 more)
  eos_OPC_Vehicle_Expense | PK: None | Vehicle_Expense_Id, Cost_Centre_Id, Expense_Month, Sr_No, Equipment_Desc, Qty, Vendor_Name, Effective_Dt, ... (+9 more)
  eos_OPC_Workshop_Repair | PK: None | Workshop_Repair_Id, Cost_Centre_Id, Expense_Month, Repair_Dt, Sr_No, Vendor, Repair_Desc, UOM, ... (+10 more)
  eos_OPC_Yard_Imprest | PK: None | Yard_Imprest_Id, Cost_Centre_Id, Expense_Month, Statement_No, Opening_Bal, Sr_No, Yard_Imprest_Dt, Voucher_No, ... (+10 more)
  eos_Orders | PK: intList | intList, OrderId, ShipCountry, OrderDate
  eos_Other_QHSE_Actions | PK: None | Other_QHSE_Action_Id, QHSE_Category_Id, ICR_No, Other_QHSE_Action_Dt, Rig_Id, Action_Recommended, Action_Taken, Action_Party, ... (+7 more)
  eos_Overtime_Dtl | PK: None | Overtime_Dtl_Id, Serv_Dtl_Id, Rig_Id, Tr_Dt, Serv_Subtype_From, Serv_Subtype_To, Serv_Type_Id, Serv_Subtype_Id, ... (+32 more)
  eos_PO_Dtl | PK: PO_Dtl_Id | PO_Dtl_Id, PO_Hdr_Id, Cost_Centre_Id, Line_Item_No, SAP_Material_Code, Item_Desc, Qty, UOM_Id, ... (+18 more)
  eos_PO_Hdr | PK: PO_Hdr_Id | PO_Hdr_Id, Project_Id, PO_No, PO_Dt, PO_Doc_Type_Id, Purchase_Group_Id, SAP_Vendor_Code, SAP_Vendor_Name, ... (+6 more)
  eos_Params_Transaction_Id_EOS | PK: Param_Name | Param_Name, Param_Value
  eos_Payroll_Cycle | PK: None | Payroll_Cycle_Id, Fs_Category_Id, Payroll_Month, Cycle_From, Cycle_To, Processing_Period_From, Processing_Period_To, Cr_User_Id, ... (+3 more)
  eos_Pms_Cert_Dtl | PK: None | Pms_Cert_Dtl_Id, Rig_Id, Pms_Grp3_Id, Equip_Cert_Id, Equip_Cert_No, Equip_Cert_Dt, Equip_Cert_Valid_Till, Equip_Cert_Type, ... (+7 more)
  eos_Prj_Drilling_Rate | PK: Prj_Drilling_Rate_Id | Prj_Drilling_Rate_Id, Drilling_Rate_Id, Prj_Contract_Id, Rig_Id, Currency_Id, Rate, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Proj_To_Cost_Centre_Mapping | PK: Proj_To_CC_Id | Proj_To_CC_Id, Project_Id, Cost_Centre_Id, From_Dt, To_Dt, Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Proj_To_User_Mapping | PK: Proj_To_User_Id | Proj_To_User_Id, Project_Id, User_Id, From_Dt, To_Dt, Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Rank_Classification | PK: None | Rank_Id, Rank_Class, Rank_Class_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Rank_To_Grade_Mapping | PK: Rank_To_Grade_Id | Rank_To_Grade_Id, Rank_Id, Grade_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Reporting_Structure | PK: None | Reporting_Structure_Id, Fs_Category_Id, Rank_Id, Reporting_Rank_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Rig_Crew_Budget | PK: None | Rig_Crew_Budget_Id, Rig_Crew_Budget_Hdr_Id, Fs_Emp_Category_Id, Cost_Centre_Id, Rank_Id, Nationality, Budgeted_Crew_Count, Currency_Id, ... (+6 more)
  eos_Rig_Crew_Budget_Hdr | PK: Rig_Crew_Budget_Hdr_Id | Rig_Crew_Budget_Hdr_Id, Prj_Contract_Id, Cost_Centre_Id, Budget_From_Dt, Budget_To_Dt, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Rig_Crew_Exceptions | PK: None | Rig_Crew_Exception_Id, Fs_Category_Id, Emp_Type_Id, Rank_Id, Fs_Emp_Id, Exception_From, Exception_To, Cr_User_Id, ... (+3 more)
  eos_Rig_Email_ID_Mapping | PK: None | Rig_Id, Rig_Dept_Id, Rank_Id, Email_Id, Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_Rig_Site_Mapping | PK: Rig_Site_Mapping_Id | Rig_Site_Mapping_Id, Rig_Id, Company_Id, Camp_Office_Addr, Contact_Fs_Emp_Id_1, Contact_Tel_No_1, Contact_Fs_Emp_Id_2, Contact_Tel_No_2, ... (+7 more)
  eos_Rig_To_Email_Mapping | PK: None | Rig_To_Email_Mapping_Id, Rig_Id, User_Id, Alert_Id, Company_Id, Addressee_Type, From_Dt, To_Dt, ... (+4 more)
  eos_Salary_Adjustment | PK: None | Salary_Adj_Id, Rig_Id, Tr_Dt, Fs_Emp_Id, Rank_Id, Emp_Type_Id, Fs_Category_Id, ED_Id, ... (+11 more)
  eos_Salary_Advise_LOP_Reversal | PK: None | LOP_Reversal_Id, Serv_Dtl_Id, Fs_Emp_Id, Old_Serv_Type_Id, Old_Serv_Subtype_Id, Old_Serv_Subtype_From, Old_Serv_Subtype_To, New_Serv_Type_Id, ... (+5 more)
  eos_Salary_Exceptions | PK: None | Salary_Exception_Id, Fs_Category_Id, Emp_Type_Id, Rank_Id, Fs_Emp_Id, Fs_New_Appl_Id, ED_Id, Exception_From, ... (+5 more)
  eos_Salary_Status | PK: None | Salary_Status_Id, Fs_Emp_Id, Cost_Centre_Id, Salary_Mth_Yr, Salary_Processed, Salary_Paid, Remarks, Cr_User_Id, ... (+3 more)
  eos_Serv_Req_Dtl | PK: None | Serv_Req_Dtl_Id, Serv_Req_Id, SR_Descr, Equip_Recd_Dt, SR_Dtl_Closed_Dt, SR_Dtl_Status, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Serv_Req_Hdr | PK: Serv_Req_Id | Serv_Req_Id, Rig_Id, Vendor_Id, Serv_Req_No, SR_Recd_Dt, Dispatch_No, Work_Order_No, Notional_Cost, ... (+10 more)
  eos_Service_Details | PK: Serv_Dtl_Id | Serv_Dtl_Id, Fs_Emp_Id, Serv_Subtype_From, Rank_Id, Serv_Type_Id, Serv_Subtype_Id, Rig_Id, Emp_Type_Id, ... (+7 more)
  eos_Service_Requisition_Dtl | PK: SR_Dtl_Id | SR_Dtl_Id, SR_Hdr_Id, SAP_No, Equip_Make_Id, Equip_Model_Id, Equip_Part_Id, Service_Desc, UOM_Id, ... (+7 more)
  eos_Service_Requisition_Hdr | PK: SR_Hdr_Id | SR_Hdr_Id, Prj_Contract_Id, Rig_id, SR_No, SR_Dt, Dept_Id, Priority, SR_Type, ... (+27 more)
  eos_Tender_Bid_Dtl | PK: None | Tender_Bid_Id, Tender_Id, Company_Id, Competitor_Id, Rig_Id, Rate_Offered, Remarks, Bid_Result, ... (+4 more)
  eos_Tender_Dtl | PK: Tender_Id | Tender_Id, Tender_No, Tender_Dt, Operator_Id, Contract_Duration, Rig_Type_Id, Rig_Capacity_HP, Drilling_Depth_FT, ... (+4 more)
  eos_Travel_Eligibility | PK: Travel_Eligibility_Id | Travel_Eligibility_Id, Fs_Category_Id, Rank_Id, Travel_Mode, Travel_Class, Travel_Preference, Eligible_From, Eligible_To, ... (+4 more)
  eos_Travel_Info_Crew | PK: Travel_Info_Crew_Id | Travel_Info_Crew_Id, Fs_Emp_Id, In_Location_Id, Out_Location_Id, Travel_Mode, Travel_Class, Travel_Info_Crew_From, Travel_Info_Crew_To, ... (+4 more)
  eos_Travel_Info_Rig | PK: Travel_Info_Rig_Id | Travel_Info_Rig_Id, Company_Id, Rig_Id, Bill_Division, Travel_Location_Id_Rig, Travel_Purpose, Authorised_By_Emp_id, Travel_Info_Rig_From, ... (+5 more)
  eos_Upload_Field_Mapping | PK: None | Upload_Field_Mapping_Id, Schema_Name, Table_Name, Table_Field_Name, Upload_Field_Name, Match_Field_Name, Field_Datatype, Field_Nullable, ... (+5 more)
  eos_User_Serv_Dtl_Exception | PK: User_Serv_Dtl_Excep_Id | User_Serv_Dtl_Excep_Id, User_Id, Fs_Emp_Id, User_Serv_Dtl_Excep_Active, CR_USER_ID, CR_DT, MOD_USER_ID, MOD_DT
  eos_Vehicle_Contracts | PK: Vehicle_Contract_Id | Vehicle_Contract_Id, Vehicle_Contract_No, Vehicle_Contract_Dt, Vendor_Id, Rental_Charges_Amt, Rental_Charges_Period, Fixed_Kms, Thereafter_Rate, ... (+10 more)
  eos_Vehicle_Log_Sheet | PK: None | Vehicle_Log_Id, Vehicle_Id, Work_Order_Id, Vehicle_Log_Dt, Starting_Kms, Closing_Kms, Remarks, Cr_User_Id, ... (+3 more)
  eos_Vehicle_Purchase_Order | PK: Purchase_Order_Id | Purchase_Order_Id, PO_No, PO_Dt, Vehicle_Contract_Id, Vendor_Id, Total_Basic_Value, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Vehicle_Work_Order | PK: Work_Order_Id | Work_Order_Id, Purchase_Order_Id, Work_Order_No, Work_Order_Dt, Cost_Centre_Id, Vehicle_Id, Unit, Rate_Per_Unit, ... (+5 more)
  eos_Warning_Letter | PK: None | Warning_Letter_Id, Fs_Emp_Id, Rig_Id, Warning_No, Warning_Letter_Dt, Reported_By, Reported_By_Rank, Remarks, ... (+7 more)
  eos_Warning_Letter_Docs | PK: None | Warning_Letter_Id, Warning_Letter_Doc_Id, Warning_Letter_Doc_Path, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Wkg_Fs_Emp_Bonus | PK: None | Fs_Emp_Id, Rank_Id, Rig_Id, Fs_Emp_Doj, Bonus_Effective_Dt, Period_From, Period_To, Bonus_Amt, ... (+1 more)
  eos_Wkg_Get_Drilling_Hdr_Id_Updated | PK: Sr_no | Sr_no, Drilling_Dtl_Id, Old_Drilling_Hdr_Id, New_Drilling_Hdr_Id, Cr_User_Id, cr_dt
  eos_Wkg_HSE_Weekly_Drill_Dtl | PK: None | HSE_Weekly_Drill_Dtl_Id, HSE_Weekly_Drill_Hdr_Id, HSE_Drill_Id, Drill_Conducted_Dt, Drill_Last_Conducted_Dt, Remarks, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_Wkg_HSE_Weekly_Drill_Hdr | PK: None | HSE_Weekly_Drill_Hdr_Id, Rig_Id, Drill_Year, Drill_Week, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_Wkg_Hazard_ID_Card_Client | PK: Haz_Card_Id | Haz_Card_Id, Haz_ID_Card_No, Prj_Contract_Id, Rig_Id, Event_Dt, Reported_By_Party, Reported_By_Fs_Emp_Id, Reported_By_Name, ... (+17 more)
  eos_Wkg_Incident_Dtl | PK: Wkg_Incident_Id | Wkg_Incident_Id, Rig_Id, Rig_Name, Unit_Name, Rig_Incident_No, Country_Id, Country, Well_No, ... (+55 more)
  eos_Wkgrp_Indicator_Type_Mapping | PK: None | Wkgrp_Ind_Type_Map_Id, Workgroup_Id, Indicator_Type_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_X_Mst_Activity | PK: Activity_Id | Activity_Id, Activity_Name, Activity_Type, Activity_Nature, Activity_Location, Intimate_Rig, Activity_Validity_Days, Activity_Active, ... (+5 more)
  eos_X_Mst_Buss_Cert | PK: Buss_Cert_Id | Buss_Cert_Id, Buss_Cert_Name, Buss_Cert_Issue_Auth_Id, Buss_Cert_Type_Id, Buss_Cert_Validity, Buss_Cert_Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_X_Mst_Equip_Cert_Authority | PK: Equip_Cert_Auth_Id | Equip_Cert_Auth_Id, Equip_Cert_Auth, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_X_Mst_Fs_Category | PK: Fs_Category_Id | Fs_Category_Id, Fs_Category_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_X_Mst_Fs_Catg_To_SSType | PK: Catg_Sstype_Id | Catg_Sstype_Id, Fs_Category_Id, Emp_Type_Id, Serv_Type_Id, Serv_Subtype_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  eos_X_Mst_Incident_Cause_OLD | PK: Incident_Cause_Id | Incident_Cause_Id, Incident_Cause_Desc, Incident_Cause_Category, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_X_Mst_Incident_Subcause | PK: Incident_Subcause_Id | Incident_Subcause_Id, Incident_Subcause, Incident_Cause_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_X_Mst_Rank | PK: Rank_id | Rank_id, Fs_Category_Id, Rig_Dept_Id, Rank_Name, Rank_Abrv, Rank_Order, Cr_User_Id, Cr_Dt, ... (+2 more)
  eos_X_Mst_Rig_Dept | PK: Rig_Dept_Id | Rig_Dept_Id, Rig_Dept_Name, Rig_Dept_Order, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_X_Mst_Serv_Subtype | PK: Serv_Subtype_Id | Serv_Subtype_Id, Serv_Subtype_Name, Serv_Subtype_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_X_Mst_Serv_Type | PK: Serv_Type_Id | Serv_Type_Id, Serv_Type_Name, Serv_Type_Abrv, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  eos_X_Mst_Vendor | PK: Vendor_Id | Vendor_Id, Vendor_Name, Vendor_Type_Id, Country_id, Vendor_Email, Currency_Id, Vendor_SAP_Code, Vendor_Active, ... (+4 more)
  eos_job_description_dtl_backup | PK: None | JD_Dtl_Id, JD_Hdr_Id, JD_Dtl_Description, JD_Dtl_Order, JD_Dtl_Active, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)

## hr (21 tables)
  hr_Emp_Additional_Dtl | PK: None | Emp_Additional_Id, Emp_Id, Res_Addr, Res_Tel_No, Residence_Country_Id, Emp_DOM, PP_No, PP_Dt, ... (+8 more)
  hr_Emp_Exit_Dtl | PK: Emp_Exit_Dtl_Id | Emp_Exit_Dtl_Id, Emp_Id, Company_Id, Probable_Exit_Dt, Financial_Year_Id, Leaving_Reason_Id, Leaving_Reason_Dtl_Id, Leaving_Reason_Actual, ... (+9 more)
  hr_Emp_Health_Checkup | PK: None | Emp_Health_Checkup_Id, Emp_Id, Checkup_Due_Dt, Checkup_Completed_Dt, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  hr_Emp_Mobile | PK: None | Emp_Mobile_Id, Emp_Id, Mobile_Make_Model, IMEI_No, Mobile_No, Mobile_Issue_Dt, Mobile_Eligible_Dt, Cr_User_Id, ... (+3 more)
  hr_Emp_Relative_Dtl | PK: None | Emp_Relative_Id, Emp_Id, Relative_Name, Relation_Id, Relative_DOB, Relative_Active, Cr_User_Id, Cr_Dt, ... (+2 more)
  hr_Emp_Service_Details | PK: Serv_Dtl_Id | Serv_Dtl_Id, EMP_ID, Serv_Dtl_From, Serv_Dtl_To, Company_Id, Business_Grp_Id, Dept_Id, Company_Loc_Id, ... (+6 more)
  hr_Intercompany_Transfer | PK: None | Intercompany_Transfer_Id, Emp_Id, From_Company_Id, To_Company_Id, Intercompany_Transfer_Dt, Financial_Year_Id, Cr_User_Id, Cr_Dt, ... (+2 more)
  hr_Mobile_Holder | PK: Mobile_Holder_Id | Mobile_Holder_Id, Mobile_No_Id, Mobile_Holder_From, Holder_Company_Id, Emp_Id, Dept_Id, Company_Loc_Id, Vessel_Id, ... (+5 more)
  hr_Mobile_Trn | PK: None | Mobile_Trn_Id, Mobile_No_Id, Vendor_Id, Holder_Company_Id, Emp_Id, Emp_Grade_Id, Dept_Id, Company_Loc_Id, ... (+14 more)
  hr_Mst_Company_CEO | PK: None | Company_CEO_Id, Company_Id, Emp_Id, CEO_From, CEO_To, Cr_User_Id, Cr_Dt, Mod_User_Id, ... (+1 more)
  hr_Mst_Conf_Room | PK: Conf_Room_Id | Conf_Room_Id, Company_Loc_Id, Conf_Room_No, Seating_Capacity, VC_Available, Conf_Room_Facilities, Cr_User_Id, Cr_Dt, ... (+2 more)
  hr_Mst_Mobile_No | PK: Mobile_No_Id | Mobile_No_Id, Mobile_No, Vendor_Id, Mobile_Type, Mobile_Ac_No, MEID_No, PESN_No, Own_Company_Id, ... (+11 more)
  hr_Mst_NonEmployee | PK: NonEmp_Id | NonEmp_Id, NonEmp_Title, NonEmp_Fname, NonEmp_Mname, NonEmp_Sname, NonEmp_Type, Company_Id, Dept_Id, ... (+15 more)
  hr_Mst_User_Company_Mapping | PK: User_Company_Map_Id | User_Company_Map_Id, User_Id, Company_Id, Business_Grp_Id, User_Company_Map_From, User_Company_Map_To, CR_USER_ID, CR_DT, ... (+2 more)
  hr_Mst_Visa | PK: Visa_Id | Visa_Id, Visa_Name, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  hr_Mst_Visa_Country | PK: None | Visa_Country_Id, Visa_Id, Country_Id, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  hr_Open_Position_Dtl | PK: Open_Position_Id | Open_Position_Id, Company_Id, Dept_Id, Company_Loc_Id, Emp_Grade_Id, Working_Designation_Id, Requisition_Dt, Open_Position_Status, ... (+6 more)
  hr_Personality_Dtl | PK: None | Personality_Id, Birth_Dt, Person_Name, Particulars, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
  hr_Probable_Joinee_Dtl | PK: Probable_Joinee_Id | Probable_Joinee_Id, Open_Position_Id, Joinee_Fname, Joinee_Mname, Joinee_Sname, Joinee_Title, Gender, Joinee_Dob, ... (+10 more)
  hr_SAP_Link_Mst_Employee | PK: None | Emp_Fname, Emp_Mname, Emp_Sname, Emp_Title, Gender, Emp_DOB, Emp_SAP_Code, Subhojit_Emp_SAP_Code, ... (+19 more)
  hr_X_Mst_Vendor | PK: Vendor_Id | Vendor_Id, Vendor_Name, Vendor_Type_Id, Country_id, Vendor_Email, Currency_Id, Vendor_SAP_Code, Vendor_Active, ... (+4 more)

## shp (1 tables)
  shp_Mst_Incident_ReportedBy | PK: Incident_ReportedBy_Id | Incident_ReportedBy_Id, Incident_ReportedBy, Cr_User_Id, Cr_Dt, Mod_User_Id, Mod_Dt
