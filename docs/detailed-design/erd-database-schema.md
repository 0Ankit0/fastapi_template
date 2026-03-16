# ERD Database Schema

```mermaid
erDiagram
  USER ||--|| NOTIFICATION_PREFERENCE : has
  USER ||--o{ NOTIFICATION_DEVICE : owns
  USER ||--o{ NOTIFICATION : receives

  USER {
    int id
    string email
    string username
  }
  NOTIFICATION_PREFERENCE {
    int id
    int user_id
    bool websocket_enabled
    bool email_enabled
    bool push_enabled
    bool sms_enabled
  }
  NOTIFICATION_DEVICE {
    int id
    int user_id
    string provider
    string platform
    string token
    string endpoint
    string subscription_id
  }
  NOTIFICATION {
    int id
    int user_id
    string title
    string body
    string type
    bool is_read
  }
```
