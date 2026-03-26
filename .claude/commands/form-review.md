# Form Review

Review a Flutter form for correct keyboard types, autofill hints, and input validation.

## Usage

```
/form-review <path-to-file>
```

## What to check

### 1. Keyboard types (`keyboardType`)

Every `TextFormField` and `TextField` should have the most specific keyboard type:

| Field type | `keyboardType` |
|-----------|----------------|
| Email | `TextInputType.emailAddress` |
| Phone | `TextInputType.phone` (or use `IntlPhoneField`) |
| URL | `TextInputType.url` |
| Number only | `TextInputType.number` |
| Multi-line text | `TextInputType.multiline` |
| Name | `TextInputType.name` |
| Password | `TextInputType.visiblePassword` (with `obscureText: true`) |
| General text | `TextInputType.text` (default, fine to omit) |

### 2. Autofill hints (`autofillHints`)

Fields inside an `AutofillGroup` should declare hints so password managers work:

| Field type | `autofillHints` |
|-----------|-----------------|
| Email | `[AutofillHints.email]` |
| Phone | `[AutofillHints.telephoneNumber]` |
| Username / display name | `[AutofillHints.username]` |
| Current password | `[AutofillHints.currentPassword]` |
| New password | `[AutofillHints.newPassword]` |
| Name | `[AutofillHints.name]` |

Wrap login/signup forms in `AutofillGroup`. Call `TextInput.finishAutofillContext()` after successful submission.

### 3. Validation (use `frontend/lib/utils/validators.dart`)

Every `TextFormField` must have a `validator`. Use the shared helpers:

```dart
import 'package:pda/utils/validators.dart' as v;

// Required field
validator: v.required()

// Compose multiple rules
validator: v.all([v.required(), v.maxLength(300)])

// Display name (letters + spaces, max 64)
validator: v.displayName()

// Optional email format check
validator: v.optionalEmail()

// Optional URL (add httpsOnly: true for external links)
validator: v.optionalUrl(httpsOnly: true)

// Role name (alphanumeric, underscores, hyphens, max 50)
validator: v.roleName()

// Max/min length standalone
validator: v.maxLength(500)
validator: v.minLength(20, 'Please write at least 20 characters')
```

For `TextField` (no form validation), enforce length with:
```dart
inputFormatters: [LengthLimitingTextInputFormatter(50000)],
```

### 4. Other checks

- Password fields: `obscureText: true` + toggle visibility icon
- `textCapitalization: TextCapitalization.sentences` for free-text fields
- `maxLines: null` + `expands: true` for full-height text areas
- Required fields labelled with `*` in `labelText`

## Instructions

Read the file at the given path. For each form field found, report:
1. Field name / label
2. Current `keyboardType` — correct or what it should be
3. `autofillHints` — present or missing (and what to add)
4. `validator` — present or missing (and what to use from `validators.dart`)
5. Any other issues

Then apply all fixes directly to the file.
