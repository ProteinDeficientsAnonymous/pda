---
name: add-perm-and-page
description: Add a new permission key and a new editable singleton page (backend model + endpoint + frontend provider + screen + route + nav + tests) to the PDA app. Use when adding a new content page that is permission-gated for editing.
argument-hint: "<permission_key> <page_slug> [\"Page Title\"]"
---

# Add Permission + Editable Page

Adds a new permission key and a corresponding editable singleton page end-to-end across the Django backend and Flutter frontend, following the exact pattern used for `edit_faq` / `faq`.

## Usage

```
/add-perm-and-page edit_faq faq "FAQ"
/add-perm-and-page edit_resources resources "Resources"
```

Arguments:
- `permission_key` — snake_case key, e.g. `edit_resources`
- `page_slug` — used in URL path and API endpoint, e.g. `resources`
- `Page Title` — human-readable label used in nav and screen copy (defaults to slug with first letter capitalised)

Derive these from the arguments before starting:
- `PermKey` = SCREAMING_SNAKE of `permission_key`, e.g. `EDIT_RESOURCES`
- `ModelName` = PascalCase of `page_slug`, e.g. `Resources`
- `NotifierName` = `ResourcesNotifier`
- `ProviderName` = `resourcesNotifierProvider`
- `ScreenClass` = `ResourcesScreen`
- `route` = `/<page_slug>`, e.g. `/resources`
- `route_name` = `page_slug`, e.g. `resources`

---

## Step 1 — Backend: `backend/users/permissions.py`

Add the new key to `PermissionKey` (in alphabetical order with the others):

```python
EDIT_RESOURCES = "edit_resources"
```

---

## Step 2 — Backend: `backend/community/models.py`

Add a singleton model after `CommunityGuidelines`. Use the exact same pattern:

```python
class Resources(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    content = models.TextField(default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resources"
        verbose_name_plural = "Resources"

    def __str__(self):
        return "Resources"

    @classmethod
    def get(cls) -> "Resources":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

---

## Step 3 — Backend: `backend/community/api.py`

Add `Resources` to the model import at the top, then add GET + PATCH endpoints immediately after the FAQ endpoints (or after the guidelines endpoints if FAQ doesn't exist). Reuse `GuidelinesOut` and `GuidelinesPatchIn` — the schema is identical.

```python
from community.models import (
    ...,
    Resources,
)

@router.get("/resources/", response={200: GuidelinesOut}, auth=JWTAuth())
def get_resources(request):
    r = Resources.get()
    return Status(200, GuidelinesOut(content=r.content, updated_at=r.updated_at))


@router.patch("/resources/", response={200: GuidelinesOut, 403: ErrorOut}, auth=JWTAuth())
def update_resources(request, payload: GuidelinesPatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_RESOURCES):
        return Status(403, ErrorOut(detail="Permission denied."))
    r = Resources.get()
    r.content = payload.content
    r.save()
    return Status(200, GuidelinesOut(content=r.content, updated_at=r.updated_at))
```

---

## Step 4 — Migration

```bash
make migrate
```

---

## Step 5 — Backend Tests: `backend/tests/test_community.py`

Pick a unique `+1202555XXXX` phone number not already used in this file. Add fixtures after the existing `edit_faq_*` fixtures, then add a test class at the bottom of the file (before the EOF, after `TestFAQ`):

```python
@pytest.fixture
def edit_resources_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550404",  # pick next available unique number
        password="resourcespass",
        display_name="Resources Editor",
    )
    role = Role.objects.create(
        name="resources_editor",
        permissions=[PermissionKey.EDIT_RESOURCES],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_resources_headers(edit_resources_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(edit_resources_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestResources:
    def test_get_resources_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/resources/", **auth_headers)
        assert response.status_code == 200
        assert "content" in response.json()
        assert "updated_at" in response.json()

    def test_get_resources_unauthenticated(self, api_client):
        response = api_client.get("/api/community/resources/")
        assert response.status_code == 401

    def test_update_resources_content(self, api_client, edit_resources_headers):
        response = api_client.patch(
            "/api/community/resources/",
            {"content": "New resources content"},
            content_type="application/json",
            **edit_resources_headers,
        )
        assert response.status_code == 200
        assert response.json()["content"] == "New resources content"

    def test_update_resources_requires_edit_resources_permission(
        self, api_client, auth_headers
    ):
        response = api_client.patch(
            "/api/community/resources/",
            {"content": "Should be denied"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_resources_requires_auth(self, api_client):
        response = api_client.patch(
            "/api/community/resources/",
            {"content": "No auth"},
            content_type="application/json",
        )
        assert response.status_code == 401
```

---

## Step 6 — Frontend Provider: `frontend/lib/providers/resources_provider.dart`

Follow `guidelines_provider.dart` exactly:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';

class Resources {
  final String content;
  final DateTime updatedAt;

  const Resources({required this.content, required this.updatedAt});

  factory Resources.fromJson(Map<String, dynamic> json) => Resources(
    content: json['content'] as String,
    updatedAt: DateTime.parse(json['updated_at'] as String),
  );
}

class ResourcesNotifier extends AsyncNotifier<Resources> {
  @override
  Future<Resources> build() async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/resources/');
    return Resources.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> saveContent(String content) async {
    final api = ref.read(apiClientProvider);
    final response = await api.patch(
      '/api/community/resources/',
      data: {'content': content},
    );
    state = AsyncData(Resources.fromJson(response.data as Map<String, dynamic>));
  }
}

final resourcesNotifierProvider =
    AsyncNotifierProvider<ResourcesNotifier, Resources>(ResourcesNotifier.new);
```

---

## Step 7 — Frontend Screen: `frontend/lib/screens/resources_screen.dart`

Follow `guidelines_screen.dart` exactly. Substitute all occurrences of `Guidelines`/`guidelines` with `Resources`/`resources`, `manage_guidelines` with `edit_resources`, and update the copy strings:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/resources_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/autosave_mixin.dart';
import 'package:pda/widgets/quill_content_editor.dart';
import 'package:pda/widgets/save_cancel_button_row.dart';

class ResourcesScreen extends ConsumerWidget {
  const ResourcesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;
    final canEdit = user?.hasPermission('edit_resources') ?? false;
    final resourcesAsync = ref.watch(resourcesNotifierProvider);

    return AppScaffold(
      child: resourcesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Text(
            'Failed to load Resources.',
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ),
        data: (resources) =>
            _ResourcesBody(content: resources.content, canEdit: canEdit),
      ),
    );
  }
}

class _ResourcesBody extends ConsumerStatefulWidget {
  final String content;
  final bool canEdit;

  const _ResourcesBody({required this.content, required this.canEdit});

  @override
  ConsumerState<_ResourcesBody> createState() => _ResourcesBodyState();
}

class _ResourcesBodyState extends ConsumerState<_ResourcesBody>
    with AutosaveMixin {
  bool _editing = false;
  late String _json;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _json = widget.content;
    if (widget.canEdit) {
      initAutosaveCallback(
        onSave: (text) =>
            ref.read(resourcesNotifierProvider.notifier).saveContent(text),
      );
    }
  }

  @override
  void dispose() {
    disposeAutosave();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ref.read(resourcesNotifierProvider.notifier).saveContent(_json);
      if (mounted) setState(() => _editing = false);
    } catch (e) {
      if (!mounted) return;
      showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _cancelEdit() {
    final saved =
        ref.read(resourcesNotifierProvider).valueOrNull?.content ??
        widget.content;
    setState(() {
      _json = saved;
      _editing = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildHeader(context),
        Expanded(
          child: QuillContentEditor(
            jsonContent: _json,
            editing: _editing,
            expands: true,
            hintText: 'Write Resources content…',
            onChanged: widget.canEdit
                ? (v) {
                    _json = v;
                    triggerAutosave(v);
                  }
                : null,
          ),
        ),
      ],
    );
  }

  Widget _buildHeader(BuildContext context) {
    if (!widget.canEdit) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
      child: Row(
        children: [
          const Spacer(),
          if (_editing) AutosaveIndicator(status: autosaveStatus),
          if (_editing) const SizedBox(width: 12),
          if (!_editing)
            FilledButton.tonal(
              onPressed: () => setState(() => _editing = true),
              child: const Text('Edit'),
            ),
          if (_editing)
            SaveCancelButtonRow(
              saving: _saving,
              onSave: _save,
              onCancel: _cancelEdit,
            ),
        ],
      ),
    );
  }
}
```

---

## Step 8 — Frontend Permission Label: `frontend/lib/screens/members/role_form_dialog.dart`

Add the new permission to the `kPermissionLabels` map so it appears in the role creation/editing dialog:

```dart
const kPermissionLabels = {
  // ... existing entries ...
  'edit_resources': 'Edit Resources',
};
```

---

## Step 9 — Frontend Router: `frontend/lib/router/app_router.dart`

(Note: steps 9-12 were originally numbered 8-11 — renumbered after inserting Step 8 above.)

Add the import with the other screen imports (alphabetical order):

```dart
import 'package:pda/screens/resources_screen.dart';
```

Add `loc == '/resources' ||` to the `isProtected` block (keep alphabetical/logical order).

Add the route after the FAQ route (or after guidelines if FAQ doesn't exist):

```dart
GoRoute(
  path: '/resources',
  name: 'resources',
  builder: (_, __) => const ResourcesScreen(),
),
```

---

## Step 9 — Frontend Nav: `frontend/lib/widgets/app_scaffold.dart`

**Wide nav** — add after the FAQ button (or after Guidelines if FAQ doesn't exist):

```dart
const _NavButton(label: 'Resources', route: '/resources'),
```

**Drawer** — add after the FAQ `_DrawerNavTile` (or after Guidelines):

```dart
_DrawerNavTile(
  item: const _DrawerItem(
    icon: Icons.menu_book_outlined,  // choose a contextually appropriate icon
    label: 'Resources',
    route: '/resources',
  ),
  currentPath: currentPath,
  theme: theme,
),
```

---

## Step 10 — Frontend Screen Test: `frontend/test/screens/resources_screen_test.dart`

Follow the pattern of `faq_screen_test.dart` exactly:

```dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/resources_provider.dart';
import 'package:pda/screens/resources_screen.dart';

const _kTestSize = Size(700, 900);

Widget _buildSubject({
  ResourcesNotifier? resourcesNotifier,
  AuthNotifier? authNotifier,
}) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => const ResourcesScreen()),
    ],
  );
  return ProviderScope(
    overrides: [
      resourcesNotifierProvider.overrideWith(
        () => resourcesNotifier ?? _FakeResourcesNotifier(),
      ),
      authProvider.overrideWith(() => authNotifier ?? _MemberAuthNotifier()),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('shows loading indicator while fetching', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(resourcesNotifier: _LoadingResourcesNotifier()),
    );
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('hides Edit button for member without edit_resources', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('Edit'), findsNothing);
  });

  testWidgets('shows Edit button for user with edit_resources permission', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(authNotifier: _ResourcesEditorAuthNotifier()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Edit'), findsOneWidget);
  });
}

class _MemberAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async =>
      const User(id: 'u1', phoneNumber: '+12025551234', displayName: 'Alice');

  @override
  Future<void> logout() async {}
}

class _ResourcesEditorAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'u2',
    phoneNumber: '+12025559003',
    displayName: 'Resources Editor',
    roles: [
      Role(id: 'r1', name: 'resources_editor', permissions: ['edit_resources']),
    ],
  );

  @override
  Future<void> logout() async {}
}

class _FakeResourcesNotifier extends ResourcesNotifier {
  @override
  Future<Resources> build() async =>
      Resources(content: '', updatedAt: DateTime(2026));
}

class _LoadingResourcesNotifier extends ResourcesNotifier {
  @override
  Future<Resources> build() async {
    await Completer<void>().future;
    return Resources(content: '', updatedAt: DateTime(2026));
  }
}
```

---

## Step 11 — Verify

```bash
make ci
```

Fix any stale tests that reference old permission strings (e.g. a test using `manage_guidelines` for an endpoint that now requires the new permission).

---

## Key Files Summary

| File | Action |
|------|--------|
| `backend/users/permissions.py` | Add `PermissionKey` entry |
| `backend/community/models.py` | Add singleton model |
| `backend/community/api.py` | Import model; add GET + PATCH endpoints |
| `backend/tests/test_community.py` | Add fixtures + `TestXxx` class |
| `frontend/lib/providers/xxx_provider.dart` | New file |
| `frontend/lib/screens/xxx_screen.dart` | New file |
| `frontend/lib/router/app_router.dart` | Import, `isProtected` entry, route |
| `frontend/lib/widgets/app_scaffold.dart` | Nav button (wide) + drawer tile |
| `frontend/test/screens/xxx_screen_test.dart` | New file |
