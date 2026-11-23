#CONSTANTS
import secure_consts


AUDIO_EXTENSIONS = {".cda", ".mp3", ".wav", ".flac", ".m4a", ".aiff" }
CD_DIRECTORY = "/Users/ChristopherArcher/Desktop/FREEDOM_ARCHIVES_Local_Test/TEST_CD"
FACT_STAGING_DIR = "/Users/ChristopherArcher/Desktop/FREEDOM_ARCHIVES_Local_Test/FREEDOM_ARCHIVES_STAGING"
FACT_BACKUP_DIR = "/Users/ChristopherArcher/Desktop/FREEDOM_ARCHIVES_Local_Test/FREEDOM_ARCHIVES_BACKUP"

# Set the service-account JSON path locally; do not commit the credential file.
GOOGLE_SERVICE_ACCOUNT_FILE = secure_consts.GOOGLE_SERVICE_ACCOUNT_FILE
GOOGLE_SPREADSHEET_TITLE = secure_consts.SPREADSHEET_TITLE
SPREADSHEET_ID = secure_consts.SPREADSHEET_ID
SHEET_ID = secure_consts.SHEET_ID
SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={SHEET_ID}"
# Configure the authorized REST API. Lookup URL must return one matching record,
# either as a JSON object or in a list under DATABASE_RECORDS_KEY. URLs may use
# {cd_call_number} and {record_id} placeholders. Set the token variable name
# below if the API requires a bearer token; never put the token itself here.
#DATABASE_LOOKUP_URL_TEMPLATE = ""
#DATABASE_UPDATE_URL_TEMPLATE = ""
#DATABASE_RECORDS_KEY = "results"
#DATABASE_RECORD_ID_FIELD = "id"
#DATABASE_RECORD_CALL_NUMBER_FIELD = "call_number"
#DATABASE_NOTES_FIELD = "notes"
#DATABASE_API_TOKEN_ENV = ""
#DATABASE_API_AUTH_HEADER = "Authorization"
#DATABASE_API_AUTH_PREFIX = "Bearer "
