using System;
using System.Data;
using System.Configuration;
using System.Collections;
using System.Web;
using System.Web.Security;
using System.Web.UI;
using System.Web.UI.WebControls;
using System.Web.UI.WebControls.WebParts;
using System.Web.UI.HtmlControls;
using System.Data.SqlClient;
using System.Text;
using System.Drawing;
using System.Security.Cryptography;
using System.Management;
using System.Security.Principal;
using System.DirectoryServices;
using SpeechLib;
using EBS_Common.Classes;
using LDAPClassLibrary.ESSAR;// LDAPClassLibrary.ESSAR.srActiveDirectory;

public partial class FrmUserLogin : System.Web.UI.Page
{
    protected void Page_Load(object sender, EventArgs e)
    {
        #region checking Session variable, if not then Creating it

        if (Session["Business_Grp_Id"] == null)
            Session.Add("Business_Grp_Id", "0");
        else
            Session["Business_Grp_Id"] = "0";

        if (Session["Company_Id"] == null)        
            Session.Add("Company_Id", "0");        
        else
            Session["Company_Id"] = "0";

        if (Session["SelectedProject"] == null)
            Session.Add("SelectedProject", "Error");
        else
            Session["SelectedProject"] = "Error";
        
        #endregion

        #region Forcible user selection
        Session["User_Id"] = "Zero";
        Session["User_Name"] = "Error User- User Login PageLoad";
        Session["SelectedProject"] = "Error";
        Session["User_Pwd"] = "Error User- User Password PageLoad";
        #endregion

        /// Set focus to the login textbox.
        if (!IsPostBack)
        {
            try
            {
                string strDomainUser = (HttpContext.Current.User).Identity.Name.ToString();
                bool BoolIsAuthenticated = (HttpContext.Current.User).Identity.IsAuthenticated;
                string strDomain = strDomainUser.Split('\\')[0].ToString();
                string strUser = strDomainUser.Split('\\')[1].ToString();
                TbLogin.Value = strUser;
           }
            catch { }

            #region Assign value to System Generic Info Fields

            String StrConnString = ConfigurationManager.ConnectionStrings["provider_glo"].ToString();
            clsSystem_Generic_Info.GetSystem_Generic_Info(StrConnString);
            lblWelCome.Text = clsSystem_Generic_Info.System_Name;  

            #endregion

            TbLogin.Focus();
        }

    }

    protected void BtnSubmit_ServerClick(object sender, System.EventArgs e)
    {
        #region Defining Local Variables
        SqlConnection Conn;
        SqlDataAdapter Da;
        SqlCommand Cmd;
        DataSet Ds;
        string strSql;
        int intUserId = 0;
        int intDaysDiff = 0;
        string strJs = "";
        string ErrorString = "";
        string strMACAddress = "";
        Boolean blnValidMACAddress = true; // currently forcing to valid mac address

        #endregion
        string ConString = ConfigurationManager.ConnectionStrings["provider_glo"].ToString();
        Conn = new SqlConnection(ConString);

        #region To fetch User Id and MAC_Address depend on entered Login Id
        #region We are considering Top 1 record, since if user_login_id is duplicate then ???
        strSql = "Select Top 1 USER_ID, MAC_Address from Mst_User Where user_login_id = @user_login_id and USER_ACTIVE='Y'";
        #endregion

        if (Conn.State != ConnectionState.Open)
            Conn.Open();

        Da = new SqlDataAdapter(strSql, Conn);
        Da.SelectCommand.Parameters.Add("user_login_id", System.Data.SqlDbType.VarChar).Value = TbLogin.Value;// Convert.ToInt32(Session["User_Id"]);
        Ds = new DataSet();
        Da.Fill(Ds, "MST_USER");
        try
        {
            intUserId = Convert.ToInt32(Ds.Tables["MST_USER"].Rows[0]["User_Id"].ToString());
        }
        catch
        {
            intUserId = 0;
        }
        #endregion

        #region if Invalid user then return
        if (intUserId == 0 || TbPassword.Value=="" )
        {
            SetErrorMsg("Invalid Credentials!");
            return;
        }
        #endregion

        #region Checking records in Password table. if not found 3 records then to check in ADS
        strSql = @"Select isnull(Count(*),0) TotRecs From Mst_User_Password Where USER_ID = @USER_ID";

        Da.SelectCommand.Parameters.Clear();
        Da.SelectCommand.CommandText = strSql;
        //Da = new SqlDataAdapter(strSql, Conn);
        Da.SelectCommand.Parameters.Add("User_Id", System.Data.SqlDbType.SmallInt).Value = intUserId.ToString();// Convert.ToInt32(Session["User_Id"]);
        Da.Fill(Ds, "ChkForTotRecsInPwdTable");
        if (Convert.ToInt16(Ds.Tables["ChkForTotRecsInPwdTable"].Rows[0]["TotRecs"]) == 3)
        {
            #region Now checkin in Password
             
             #region Commented old query
             //            strSql = @"Select USER_ID from Mst_User Where USER_ID =
//                            (
//                               Select top 1 USER_ID from Mst_User_Password Where Password_Text = '" + TbPassword.Value + "' and USER_ID = " + intUserId.ToString() +
//                              " and PASSWORD_DATE = (Select Max(PASSWORD_DATE) from Mst_User_Password Where USER_ID=" + intUserId.ToString() + " ) " +
             //                             ")";
             #endregion
             
             strSql = @"Select PWD from dbo.Mst_User_Password Where USER_ID = " + intUserId.ToString() + 
                       "  and PASSWORD_DATE = (Select Max(PASSWORD_DATE) from dbo.Mst_User_Password Where USER_ID = " + intUserId.ToString() + " ) " + "";

            if (Conn.State != ConnectionState.Open)
                Conn.Open();

            #region Enctypting
            //MD5CryptoServiceProvider md5Hasher = new MD5CryptoServiceProvider();
            //UTF8Encoding encoder = new UTF8Encoding();
            //byte[] hashedBytes;
            //hashedBytes = md5Hasher.ComputeHash(encoder.GetBytes(TbPassword.Value));
            #endregion

            //Da = new SqlDataAdapter(strSql, Conn);
            Da.SelectCommand.Parameters.Clear();
            Da.SelectCommand.CommandText = strSql;
            //Ds = new DataSet();
            //Da.SelectCommand.Parameters.Add("PASSWORD", SqlDbType.Binary, 16).Value = hashedBytes;

            Da.Fill(Ds, "ChkInPwdTable");
            LblError.Text = "";
            #region No records found then return

            if (Ds.Tables["ChkInPwdTable"].Rows.Count <= 0)
            {
                SetErrorMsg("Invalid Credentials!");
                return;
            }
            else
            {
                
                #region Decrytion using TripleDESCryptoServiceProvider and MD5CryptoServiceProvider Crytography Algorithm 
                string strDecryptPassword = SSTCryptographer.Decrypt(Ds.Tables["ChkInPwdTable"].Rows[0]["PWD"].ToString());
                #endregion

                if (strDecryptPassword != TbPassword.Value)               //Check if Decryt Password same as input password 
                {
                    SetErrorMsg("Invalid Credentials!");
                    return;
                }
            }
            #endregion
            #endregion

            #region Setting User id, Name
            Session["User_Id"] = intUserId.ToString();// Ds.Tables["MST_USER"].Rows[0]["User_Id"].ToString();
            //Session["User_Name"] = Ds.Tables["MST_USER"].Rows[0]["User_Name"].ToString();
            #endregion

            #region If last changed pwd is < 30 days then force user to change it
            strSql = "Select datediff(dd, Max(PASSWORD_DATE), GETDATE()) DaysDiff From Mst_User_Password Where USER_ID=" + intUserId.ToString();

            try
            {
                Cmd = new SqlCommand(strSql, Conn);

                if (Conn.State != ConnectionState.Open)
                    Conn.Open();

                intDaysDiff = Convert.ToInt16(Cmd.ExecuteScalar());
            }
            catch
            {
                intDaysDiff = 100;
            }
            if (intDaysDiff >= 30)
            {
                // Opening form in separate page & then closing it.
                strJs = "<script>alert('Password has Expired, kindly change it.');  window.open('frmChangePwd.aspx";
                strJs += "', target='_blank','location =no, menubar =no,toolbar =no,resizable=yes,status=yes,scrollbars=yes');</script>";
                ClientScript.RegisterClientScriptBlock(this.GetType(), "ChangePwd" + DateTime.Now.ToString("ddMMyyyyHHmmss"), strJs);
                return;
            }
            #endregion
        }
        else
        {
            #region Now checking in ADS
            #region checking Authentication with Active Directory Services
            try
            {
                bool blnCheck = IsAuthenticated_LDAP("SRHOUSE",
                                           TbLogin.Value,
                                           TbPassword.Value);


                
            }
            catch (SqlException sqlexep)
            {
                SetErrorMsg(sqlexep.Message.ToString());
                //ErrorString = new EBS_Common.Classes.clsExceptionHandling().getErrorScript(sqlexep, ref Conn);
                //ClientScript.RegisterClientScriptBlock(this.GetType(), "Error", ErrorString);
                return;
            }
            catch (Exception exep)
            {
                try
                {
                    bool blnCheck = IsAuthenticated("SRHOUSE",
                                               TbLogin.Value,
                                               TbPassword.Value);
                }
                catch (SqlException sqlexep_ldap)
                {
                    SetErrorMsg(sqlexep_ldap.Message.ToString());
                    //ErrorString = new EBS_Common.Classes.clsExceptionHandling().getErrorScript(sqlexep, ref Conn);
                    //ClientScript.RegisterClientScriptBlock(this.GetType(), "Error", ErrorString);
                    return;
                }
                catch (Exception exep_ldap)
                {
                    SetErrorMsg(exep_ldap.Message.ToString());
                    //ErrorString = new EBS_Common.Classes.clsExceptionHandling().getErrorScript(exep, ref Conn);
                    //ClientScript.RegisterClientScriptBlock(this.GetType(), "Error", ErrorString);
                    return;
                }

                //SetErrorMsg(exep.Message.ToString());
                //ErrorString = new EBS_Common.Classes.clsExceptionHandling().getErrorScript(exep, ref Conn);
                //ClientScript.RegisterClientScriptBlock(this.GetType(), "Error", ErrorString);
                //return;
            }

            #endregion
            #endregion
        }
        #endregion

        #region Setting User id
        Session["User_Id"] = intUserId.ToString();// Ds.Tables["MST_USER"].Rows[0]["User_Id"].ToString();
        #endregion

        #region Setting Name with Title
        strSql = @"Select E.Emp_Title + ' ' + E.Emp_Fname + ' ' + E.Emp_Mname + ' ' + E.Emp_Sname [Name] From dbo.Mst_Employee E, dbo.Mst_User U
                   Where E.Emp_Id = U.Emp_Id and U.User_Id = @User_Id;
	Select  ' ' + NE.NonEmp_Fname + ' ' + NE.NonEmp_Mname + ' ' + NE.NonEmp_Sname [Name] From HR.Mst_NonEmployee NE, dbo.Mst_User U 
                Where NE.NonEmp_Id = U.NONEMP_ID and U.User_Id =@User_Id";

        //Da = new SqlDataAdapter(strSql, Conn);
        Da.SelectCommand.Parameters.Clear();
        Da.SelectCommand.CommandText = strSql;
        Da.SelectCommand.Parameters.Add("User_Id", System.Data.SqlDbType.SmallInt).Value = intUserId.ToString();// Convert.ToInt32(Session["User_Id"]);
        Da.Fill(Ds, "Employee");
        if (Ds.Tables["Employee"].Rows.Count > 0)
        {
            Session["User_Name"] = Ds.Tables["Employee"].Rows[0]["Name"].ToString();
        }
        else if (Ds.Tables["Employee1"].Rows.Count > 0)
        {
            Session["User_Name"] = Ds.Tables["Employee1"].Rows[0]["Name"].ToString();
        }

        Session["User_Pwd"] = TbPassword.Value.ToString();
        #endregion

        if ((intUserId == 1) || (intUserId == 470) || (intUserId == 3) || (intUserId == 222) || (intUserId == 223) || (intUserId == 224))            
            Sound_Alert_NewUser_Login();

        #region Commented
//        strSql = @"Select USER_ID, User_Name, MAC_Address from Mst_User where USER_ID =
//                (
//            Select top 1 USER_ID from Mst_User_Password where user_password = @PASSWORD and USER_ID = " + intUserId.ToString() +
//            " and PASSWORD_DATE = (Select Max(PASSWORD_DATE) from Mst_User_Password where USER_ID=" + intUserId.ToString() + " ) " +
//            ")";

//        if (Conn.State != ConnectionState.Open)
//            Conn.Open();

//        #region Enctypting
//        MD5CryptoServiceProvider md5Hasher = new MD5CryptoServiceProvider();
//        UTF8Encoding encoder = new UTF8Encoding();
//        byte[] hashedBytes;
//        hashedBytes = md5Hasher.ComputeHash(encoder.GetBytes(TbPassword.Value));
//        #endregion

//        Da = new SqlDataAdapter(strSql, Conn);
//        Ds = new DataSet();
//        Da.SelectCommand.Parameters.Add("PASSWORD", SqlDbType.Binary, 16).Value = hashedBytes;

//        Da.Fill(Ds, "MST_USER");
//        LblError.Text = "";
//        if (Ds.Tables["MST_USER"].Rows.Count <= 0)
//        {
//            Session["User_Id"] = "0";
//            Session["User_Name"] = "0 User (User Login)";

//            TbPassword.Focus();
//            LblError.Text = "Invalid Credentials!";
//            if (LblError.ForeColor == Color.Red)
//                LblError.ForeColor = Color.Blue;
//            else
//                LblError.ForeColor = Color.Red;

//        }//if (Ds.Tables["MASTER_USER"].Rows.Count<= 0 )
//        else
//        {
//            #region Setting User id, Name
//            Session["User_Id"] = Ds.Tables["MST_USER"].Rows[0]["User_Id"].ToString();
//            Session["User_Name"] = Ds.Tables["MST_USER"].Rows[0]["User_Name"].ToString();
//            #endregion

//            #region Setting  Name with Title
//            strSql = @"Select E.Emp_Title + ' ' + E.Emp_Fname + ' ' + E.Emp_Mname + ' ' + E.Emp_Sname [Name] From dbo.Mst_Employee E, dbo.Mst_User U
//                       Where E.Emp_Id = U.Emp_Id and U.User_Id = @User_Id";

//            Da = new SqlDataAdapter(strSql, Conn);
//            Da.SelectCommand.Parameters.Add("User_Id", System.Data.SqlDbType.SmallInt).Value = intUserId.ToString();// Convert.ToInt32(Session["User_Id"]);
//            Da.Fill(Ds, "Employee");
//            if (Ds.Tables["Employee"].Rows.Count > 0)
//            {
//                Session["User_Name"] = Ds.Tables["Employee"].Rows[0]["Name"].ToString();
//            }
//            #endregion

//            #region If last changed pwd is < 30 days then force user to change it
//            strSql = "Select datediff(dd, Max(PASSWORD_DATE), GETDATE()) DaysDiff from Mst_User_Password where USER_ID=" + intUserId.ToString() ;

//            try
//            {
//                Cmd = new SqlCommand(strSql, Conn);

//                if (Conn.State != ConnectionState.Open)
//                    Conn.Open();

//                intDaysDiff = Convert.ToInt16(Cmd.ExecuteScalar());
//            }
//            catch
//            {
//                intDaysDiff = 100;
//            }
//            if (intDaysDiff >= 30)
//            {
//                // Opening form in separate page & then closing it.
//                strJs = "<script>alert('Password has Expired, kindly change it.');  window.open('frmChangePwd.aspx";
//                strJs += "', target='_blank','location =no, menubar =no,toolbar =no,resizable=yes,status=yes,scrollbars=yes');</script>";
//                ClientScript.RegisterClientScriptBlock(this.GetType(), "ChangePwd" + DateTime.Now.ToString("ddMMyyyyHHmmss"), strJs);
//                return;
//            }
//            #endregion

//        }
        #endregion

        LblError.Text = "Welcome " + Session["User_Name"].ToString();

        #region Checking MAC Address Related

        #region Checking MAC Address
        if (Conn.State != ConnectionState.Open)
            Conn.Open();

        #region We get MAC Address like 00-25-B3-4B-56-63 from ipconfig /all option. But with .net we get 00:25:B3:4B:56:63, so we are replacing - with :
        strMACAddress = Ds.Tables["MST_USER"].Rows[0]["MAC_Address"].ToString().Replace('-', ':');
        #endregion


        #region Checking MAC Address - Commented
        //ManagementClass oMClass = new ManagementClass("Win32_NetworkAdapterConfiguration");
        //ManagementObjectCollection colMObj = oMClass.GetInstances();
        //blnValidMACAddress = false;
        //foreach (ManagementObject objMO in colMObj)
        //{
        //    //TextBox1.Text += "\n" + objMO["Caption"].ToString();
        //    try
        //    {
        //        //TextBox1.Text += " -> " + objMO["MacAddress"].ToString();
        //        if (objMO["MacAddress"].ToString() == strMACAddress)
        //        {
        //            blnValidMACAddress = true;
        //        }
        //    }
        //    catch
        //    { }
        //}
        #endregion
        //if (blnValidMACAddress == true)
        //{
        //    LblError.Text += " Valid MAC Address " + strMACAddress;
        //}
        //else
        //{
        //    LblError.Text += " InValid MAC Address " + strMACAddress;
        //}

        #endregion
        #region Tracking User Access Log
        string strAccess_Type = "N";
        int intNr_User_Id = 0;

        if (Conn.State != ConnectionState.Open)
            Conn.Open();
        Cmd = new SqlCommand(strSql, Conn);

        #region Setting strAccess_Type for Regular / Non regular.
        if (blnValidMACAddress == true)
        {
            strAccess_Type = "R";
        }
        else
        {
            strAccess_Type = "N";
            #region Now to fetch from whose pc system got used
            strSql = "Select USER_ID from Mst_User Where MAC_Address= @MAC_Address";

            try
            {
                if (Conn.State != ConnectionState.Open)
                    Conn.Open();
                Cmd.Parameters.Clear();
                Cmd.CommandText = strSql;
                Cmd.Parameters.Add("MAC_Address", System.Data.SqlDbType.VarChar).Value = strMACAddress.Replace(':', '-');

                intNr_User_Id = Convert.ToInt16(Cmd.ExecuteScalar());
            }
            catch
            {
                intNr_User_Id = 0;
            }
            #endregion
        }
        #endregion
        ///Commented this section as on date : 08/03/2016
        //if ((intUserId == 1) || (intUserId == 2) || (intUserId == 3) || (intUserId == 222) || (intUserId == 223) || (intUserId == 224))
        //{ }
        //else
        //{

            //#region Inserting in user access log
            //strSql = @"Insert into dbo.User_Access_Dtl (
                //User_Id ,Access_Dt ,Access_Type ,Nr_User_Id )
                //Values (@User_Id ,getdate(),@Access_Type ,@Nr_User_Id)";
            //Cmd.Parameters.Clear();
            //Cmd.CommandText = strSql;

            //Cmd.Parameters.Add("User_Id", System.Data.SqlDbType.SmallInt).Value = intUserId;
            //Cmd.Parameters.Add("Access_Type", System.Data.SqlDbType.Char).Value = Convert.ToChar(strAccess_Type);
            //if (intNr_User_Id > 0)
            //{
            //    Cmd.Parameters.Add("Nr_User_Id", System.Data.SqlDbType.SmallInt).Value = intNr_User_Id;
            //}
            //else
            //{
            //    Cmd.Parameters.Add("Nr_User_Id", System.Data.SqlDbType.SmallInt).Value = DBNull.Value;
            //}
            //Cmd.ExecuteNonQuery();
            //#endregion
        //}
        #endregion

        #endregion
        // Server.Transfer("frmSelectProjects.aspx",true);
        string strSystemURL = ConfigurationManager.ConnectionStrings["SystemURL"].ToString();

        //            string strJs = "<script>window.open('" + strSystemURL + "/" + "frmSelectProjects.aspx";// + strURL;
        strJs = "<script>window.open('" + strSystemURL + "/" + "frmProject_Navigator.aspx";// + strURL;
        strJs += "', target='_self','location =no, menubar =no,toolbar =no,resizable=yes,status=yes,scrollbars=yes');</script>";
        ClientScript.RegisterClientScriptBlock(this.GetType(), "Project_Navigator" + DateTime.Now.ToString("ddMMyyyyHHmmss"), strJs);

        if (Conn.State == ConnectionState.Open)
            Conn.Close();
        Conn.Dispose();
    }

    public bool IsAuthenticated(string domain, string username, string pwd)
    {
        try
        {
            string  cmStr ="" ;
            LDAPClassLibrary.ESSAR.srActiveDirectory ADL = new LDAPClassLibrary.ESSAR.srActiveDirectory();
            cmStr = ADL.IsAuthenticated(username, pwd);
            Array cmAry =null;
            cmAry = cmStr.Split('|');
            if (cmStr[0].ToString().ToUpper() =="F")
            {
                throw new Exception(".");
            }
        }
        catch (Exception ex)
        {
            throw new Exception("Error authenticating user. " + ex.Message);
        }
        return true;
    }

    public bool IsAuthenticated_LDAP(string domain, string username, string pwd)
    {
        string _filterAttribute;

        string _path = "LDAP://" + domain;
        string domainAndUsername = domain + @"\" + username;
        DirectoryEntry entry = new DirectoryEntry(_path,
                                                   domainAndUsername,
                                                     pwd);

        try
        {
            // Bind to the native AdsObject to force authentication.
            Object obj = entry.NativeObject;
            DirectorySearcher search = new DirectorySearcher(entry);
            search.Filter = "(SAMAccountName=" + username + ")";
            search.PropertiesToLoad.Add("cn");
            SearchResult result = search.FindOne();
            if (null == result)
            {
                return false;

            }
            // Update the new path to the user in the directory
            _path = result.Path;
            _filterAttribute = (String)result.Properties["cn"][0];
        }
        catch (Exception ex)
        {
            throw new Exception("Error authenticating user. " + ex.Message);
        }
        return true;
    }

    private void SetErrorMsg(string strMsg)
    {
        Session["User_Id"] = "0";
        Session["User_Name"] = "0 User (User Login)";
        Session["User_Pwd"] = "0 User (User Password)";
        TbPassword.Focus();
        LblError.Text = strMsg;// "Invalid Credentials!";
        if (LblError.ForeColor == Color.Red)
            LblError.ForeColor = Color.Blue;
        else
            LblError.ForeColor = Color.Red;
    }

    protected void Sound_Alert_NewUser_Login()
    {
        try
        {
            SpVoice voice = new SpVoice();
            voice.Speak("Welcome " + Session["User_Name"].ToString() + " to " + clsSystem_Generic_Info.System_Name  + ".", SpeechVoiceSpeakFlags.SVSFDefault);
            voice.Volume = 100;
            voice.Rate = -5;
            voice.Priority = SpeechVoicePriority.SVPAlert;
            SpeechLib.SpAudioFormat spaf = new SpeechLib.SpAudioFormat();
            spaf.Type = SpeechAudioFormatType.SAFT48kHz16BitStereo;
        }
        catch(Exception ex )
        {}
    }

}
