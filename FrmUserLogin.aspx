<%@ Page Language="C#" MasterPageFile="~/FrmMasterPage.master" AutoEventWireup="true"
    CodeFile="FrmUserLogin.aspx.cs" Inherits="FrmUserLogin" Title="User Login" %>

<asp:Content ID="Content1" ContentPlaceHolderID="cntOpenWindow" runat="Server">

    <script type="text/javascript" language="javascript" src="JavaScript/generic.js"> </script>
    
    <script language="javascript" type="text/javascript">
        window.onload = JavaScriptCheck;
        
        function TrimMe(obj) {
            //alert(obj.value);
            obj.value = alltrim(obj.value);
            return true;
        }
        
        function CheckForEnterKey(e) {
            var evt = e || window.event;
            if (evt.keyCode == 13) {
                document.getElementById('<%=BtnSubmit.ClientID%>').click(); 
                return true;
            }
        }
        function JavaScriptCheck() {
            document.getElementById('<%=BtnSubmit.ClientID%>').disabled = '';
        }

    </script>

    <noscript>
        <%--<meta http-equiv="REFRESH" content="0;url='HTMLPage.htm'">--%>
        Your browser does not support JavaScript!
        
    </noscript>
    
    <table align="center" border="0" cellpadding="1" cellspacing="1" class="table" style="width: 100%;
        height: 100%;" onload="temp()">
        <tr style="width: 100%;">
            <td colspan="5" class="td_center" style="background-image: url(Images/Background/panel_br.png);">
                <asp:Label ID="lblWelCome" runat="server"  Style="font-family: Verdana, Arial, 'Times New Roman';
                    font-size: 11pt; color: #E6F2FF;"></asp:Label>
            </td>
        </tr>
        <tr>
            <td class="td_center" style="width: 20%; vertical-align: top;">
                <table>
                    <tr>
                        <td class="td_center">
                            &nbsp;
                        </td>
                    </tr>
                    <tr>
                        <td class="td_center" style="color: #ffffff; width: 100%; height: 20px; background-image: url(Images/Background/panel_br.png);">
                            User ID
                        </td>
                    </tr>
                    <tr>
                        <td class="td_center" style="width: 100%">
                            <input id="TbLogin" runat="server" class="textbox" maxlength="50" name="login" onfocus="nextfield ='TbPassword';" onblur="TrimMe(this);" />
                        </td>
                    </tr>
                    <tr>
                        <td class="td_center" style="color: #ffffff; width: 100%; height: 20px; background-image: url(Images/Background/panel_br.png);">
                            Password
                        </td>
                    </tr>
                    <tr>
                        <td class="td_center" style="width: 100%;">
                            <input id="TbPassword" runat="server" class="textbox_PWD" maxlength="32" name="passwd"
                                type="password" onkeydown="CheckForEnterKey();" onblur="TrimMe(this);"  />
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2" align="center" height="33">
                            <input id="BtnSubmit" runat="server" class="td_button" name=".save" onserverclick="BtnSubmit_ServerClick"
                                type="submit" value="Sign In" style="width: 75px; height: 23px;" disabled="disabled" />&nbsp;
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <asp:Label ID="LblError" runat="server" Font-Bold="True" ForeColor="Blue" 
                                Width="220px" Height="59px"></asp:Label>
                        </td>
                    </tr>
                </table>
                <td class="td" style="width: 15%; vertical-align: top; background-color: #000000;"
                    align="center">
                    <table align="center">
                        <tr style="width: 100%; height: 100%;">
                            <td class="td_center">
                                <img src="Images/Business.jpg" height="115px" width="150" />
                            </td>
                        </tr>
                        <tr>
                            <td class="td_center" style="background-image: url(Images/Background/panel_br.png);
                                color: #ffffff;">
                                SEROS</td>
                        </tr>
                    </table>
                     
                    <table align="center">
                        <tr style="width: 100%; height: 100%;">
                            <td class="td_center">
                                <img src="Images/Energy.jpg" height="115px" width="150" />
                            </td>
                        </tr>
                        <tr>
                            <td class="td_center" style="background-image: url(Images/Background/panel_br.png);
                                color: #ffffff;">
                                Energy
                            </td>
                        </tr>
                    </table>
                    <table align="center">
                        <tr style="width: 100%; height: 100%;">
                            <td class="td_center">
                                <img src="Images/ShipPortLog.jpg" height="115px" width="150" />
                            </td>
                        </tr>
                        <tr>
                            <td class="td_center" style="background-image: url(Images/Background/panel_br.png);
                                color: #ffffff;">
                                Shipping&nbsp;
                            </td>
                        </tr>
                    </table>

                    <table align="center">
                        <tr style="width: 100%; height: 100%;">
                            <td class="td_center">
                                <img src="Images/SerosLogistic.jpg" height="115px" width="150" />
                            </td>
                        </tr>
                        <tr>
                            <td class="td_center" style="background-image: url(Images/Background/panel_br.png);
                                color: #ffffff;">
                                &nbsp;Logistics&nbsp;
                            </td>
                        </tr>
                    </table>
                     
                </td>
                <td class="td_section" style="width: 65%; vertical-align: top;">
                    <table>
                        <%--                    <tr><td class="td_center" style="background-image:url(Images/Background/panel_br.png); color:#ffffff; height:25px; font-size:larger;">E S S A R</td></tr>
--%>
                        <tr>
                            <td style="width: 100%;">
                                <img src="Images/Business_Seros.jpg" />
                            </td>
                        </tr>
                        <tr>
                            <td class="td_normal">
                                <br />
                                <b>Our vision</b>
                                <br />
                                We will be a respected global entrepreneur, through the power of positive action.
                                <br />
                                <br />
                                <b>Our mission </b>
                                <br />
                                We are committed to innovative growth, through our personal passion, reinforced
                                by a professional mindset, creating value for all those we touch.
                                <br />
                                <br />
                                <b>Our spirit</b>
                                <br />
                                The Seros Group has changed significantly in recent years and continues to evolve,
                                to keep pace with the changing times. We have undertaken a sustainable journey of
                                transformation by foraying into new international markets, and exploring new business
                                areas in a bid to keep our entrepreneurial spirit alive, and to continue growing.
                                <br />
                                <br />
                                To mark the phenomenal growth witnessed over the last four decades, the Group recently
                                unveiled its new brand identity marking a very important milestone in its journey
                                and reflecting a new beginning for the Group. A new brand identity reinforces all
                                the positives to fulfill our vision to be a global entrepreneur through the power
                                of positive action.
                                <br />
                                <br />
                                We aim to have a robust value system comprising positive attitude, positive action
                                and positive achievement.
                                <br />
                                <br />
                                We endeavor to create enduring value for customers and stakeholders in core manufacturing
                                and service businesses, through world-class operating standards, state-of-the-art
                                technology and the �positive attitude� of our people.
                                <br />
                                <br />
                                Privately owned and professionally managed, the Group is judiciously invested in
                                the commodity, annuity and services businesses. Forward and backward integration,
                                the use of state-of-the-art technology, in-house research and innovation have made
                                Seros Global a force to reckon with in each of its businesses.
                                <br />
                                <br />
                                Finally, the Seros way is all about keeping its entrepreneurial spirit alive, and
                                to keep growing with a passion to progress and the power to succeed with a renewed
                                strength of purpose and commitment.
                            </td>
                        </tr>
                    </table>
                </td>
                </td> 
        </tr>
        <tr>
            <td colspan="5" align="center" style="height: 30px">
                &nbsp;
                <%--value 0 means enable 1 means not enable --%>
                <input type="hidden" id="tbchk_javascript_status_Hidden" value="0" runat="server" />
            </td>
        </tr>
    </table>
    <%--</div>
--%>
</asp:Content>



