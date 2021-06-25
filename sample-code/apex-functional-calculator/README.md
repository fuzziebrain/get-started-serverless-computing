# APEX with Oracle Functions Demo

The Oracle Function application *calculator* and function *add* must be deployed. You can find the code in this [directory](../calculator).

Also, setup an OCI Web Credential. You can find details on how to do that [here](https://blogs.oracle.com/oraclemagazine/better-file-storage-in-oracle-cloud).

The code below can be found on Page 1, in the dynamic action *onClickPerformAdd*:

```sql
declare
  l_response clob;
  -- TOOD: Template URL: https://<UNIQUE_STRING>.<REGION>.functions.oci.oraclecloud.com
  l_base_url varchar2(200) := 'https://<UNIQUE_STRING>.<REGION>.functions.oci.oraclecloud.com';
  -- TODO: Obtain the Function's OCID and put it here:
  l_function_ocid varchar2(200) := '<FUNCTION_OCID>';
begin
  apex_web_service.g_request_headers(1).name := 'Content-Type';
  apex_web_service.g_request_headers(1).value := 'application/json';
  apex_web_service.g_request_headers(2).name := 'fn-intent';
  apex_web_service.g_request_headers(2).value := 'httprequest';
  apex_web_service.g_request_headers(3).name := 'fn-invoke-type';
  apex_web_service.g_request_headers(3).value := 'sync';

  l_response := apex_web_service.make_rest_request(
    p_http_method => 'POST'
    , p_url => l_base_url || replace(
        '/20181201/functions/{functionId}/actions/invoke'
        , '{functionId}'
        , l_function_ocid
      )
    , p_body => json_object(
        'first_addend' value to_number(:P1_FIRST_ADDEND)
        , 'second_addend' value to_number(:P1_SECOND_ADDEND)
      )
    -- TODO: Create the OCI web credential and enter its static ID below:
    , p_credential_static_id => '<WEB_CREDENTIAL_STATIC_ID>'
  );

  apex_json.parse(l_response);

  return apex_json.get_number(p_path => 'sum');
end;
```