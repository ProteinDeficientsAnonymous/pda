class DocumentSummary {
  final String id;
  final String title;
  final int displayOrder;
  final DateTime updatedAt;

  const DocumentSummary({
    required this.id,
    required this.title,
    required this.displayOrder,
    required this.updatedAt,
  });

  factory DocumentSummary.fromJson(Map<String, dynamic> json) {
    return DocumentSummary(
      id: json['id'] as String,
      title: json['title'] as String,
      displayOrder: json['display_order'] as int,
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}

class DocFolder {
  final String id;
  final String name;
  final String? parentId;
  final int displayOrder;
  final List<DocFolder> children;
  final List<DocumentSummary> documents;

  const DocFolder({
    required this.id,
    required this.name,
    this.parentId,
    required this.displayOrder,
    this.children = const [],
    this.documents = const [],
  });

  factory DocFolder.fromJson(Map<String, dynamic> json) {
    return DocFolder(
      id: json['id'] as String,
      name: json['name'] as String,
      parentId: json['parent_id'] as String?,
      displayOrder: json['display_order'] as int,
      children:
          (json['children'] as List<dynamic>?)
              ?.map((e) => DocFolder.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      documents:
          (json['documents'] as List<dynamic>?)
              ?.map((e) => DocumentSummary.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class Document {
  final String id;
  final String title;
  final String content;
  final String contentHtml;
  final String folderId;
  final int displayOrder;
  final String? createdById;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Document({
    required this.id,
    required this.title,
    required this.content,
    required this.contentHtml,
    required this.folderId,
    required this.displayOrder,
    this.createdById,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'] as String,
      title: json['title'] as String,
      content: json['content'] as String,
      contentHtml: json['content_html'] as String? ?? '',
      folderId: json['folder_id'] as String,
      displayOrder: json['display_order'] as int,
      createdById: json['created_by_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}
