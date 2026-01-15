# Storage Data Access Layer

This package defines the data-access layer for survey storage under `src/storage/`.

## Models

| Schema | Fields |
| --- | --- |
| `question_bank` | `id`, `category`, `type`, `question_text`, `keyword` |
| `survey_info` | `client_name`, `course_name`, `manager`, `date`, `category`, `survey_name` |
| `responses` | `survey_id`, `respondent_id`, `question_id`, `answer_value` |

## Drivers

### Google Sheets (Phase 1)

Use `GoogleSheetsDriver` to read/write Google Sheets tabs. Each table is stored in a worksheet with the same name.

### BigQuery (Phase 2)

`BigQueryDriver` is the abstract interface for future BigQuery support. The `BigQueryAdapter` provides a concrete implementation and can be swapped in when ready.

## CRUD Signatures for Streamlit Usage

```python
from storage.google_sheets import GoogleSheetsDriver
from storage.config import StorageConfig
from storage.repository import StorageRepository

config = StorageConfig(
    backend="sheets",
    sheet_id="<google-sheet-id>",
    credentials_json="<service-account-json>",
)

repo = StorageRepository(driver=GoogleSheetsDriver(config))

# Question bank
repo.list_question_bank()  # -> pandas.DataFrame
repo.create_question_bank([
    {
        "id": "Q-001",
        "category": "운영",
        "type": "likert",
        "question_text": "강의 시간이 적절했나요?",
        "keyword": "시간",
    }
])
repo.replace_question_bank([...])

# Survey info
repo.list_survey_info()
repo.create_survey_info([
    {
        "client_name": "ACME",
        "course_name": "리더십",
        "manager": "홍길동",
        "date": "2024-01-01",
        "category": "리더십",
        "survey_name": "리더십 만족도",
    }
])
repo.replace_survey_info([...])

# Responses
repo.list_responses()
repo.create_responses([
    {
        "survey_id": "S-001",
        "respondent_id": "R-001",
        "question_id": "Q-001",
        "answer_value": "5",
    }
])
repo.replace_responses([...])
```
