// APP_SHUTDOWN is a Zotero bootstrap constant not in zotero-types
declare let APP_SHUTDOWN: number;

// Single source of truth for the places where zotero-types under-models fields that
// Zotero accepts at runtime. Each helper owns exactly one runtime-contract widening so
// the rest of the file reads cleanly typed instead of scattering casts.

// Zotero accepts `false` for Collection.parentKey to detach a collection from its
// parent, but zotero-types models the field as `string`. This is the single owned site
// that writes that runtime contract; callers go through it instead of casting.
function setCollectionParentKey(collection: Zotero.Collection, parentKey: string | false): void {
  (collection as { parentKey: string | false }).parentKey = parentKey;
}

// Tags.js guards `if (onProgress)` and `if (types)`, so both are optional at runtime;
// zotero-types incorrectly marks them required. This is the single owned site that calls
// removeFromLibrary against its real two-argument contract.
function removeTagsFromUserLibrary(libraryID: number, tagIDs: number[]): Promise<void> {
  const remove = Zotero.Tags.removeFromLibrary as (
    this: typeof Zotero.Tags,
    libraryID: number,
    tagIDs: number[],
  ) => Promise<void>;
  return remove.call(Zotero.Tags, libraryID, tagIDs);
}

// A Zotero HTTP endpoint is registered as a constructor function whose prototype carries
// the request metadata and init handler. The slot is cleared to undefined on shutdown.
type EndpointPrototype = {
  supportedMethods: string[];
  supportedDataTypes?: string[];
  init: (...args: never[]) => void | Promise<void>;
};
type EndpointConstructor = { (): void; prototype: EndpointPrototype };

let AttachEndpoint: EndpointConstructor | undefined;
let WriteEndpoint: EndpointConstructor | undefined;
let VersionEndpoint: EndpointConstructor | undefined;

declare const PLUGIN_VERSION: string;
declare const FULLTEXT_ATTACH_PATH: string;
declare const LOCAL_WRITE_PATH: string;
declare const VERSION_PATH: string;
declare const FULLTEXT_ALLOWED_DIRS: string[];
declare const ADDON_ID: string;
declare const HOMEPAGE_URL: string;
declare const UPDATE_URL: string;
declare const STRICT_MIN_VERSION: string;
declare const STRICT_MAX_VERSION: string;
declare const TESTED_ZOTERO_VERSION: string;
const PLUGIN_CAPABILITIES = [
  "attach",
  "attach_bytes",
  "write",
  "version_probe",
  "health_probe",
  "import_bibtex",
  "import_by_identifier",
  "selected_collection",
  "sync",
  "run_javascript",
];

const BIBTEX_TRANSLATOR_ID = "9cb70025-a888-4a29-a210-93ec52da40d4";

type RequestData = Record<string, unknown>;
type SendResponse = (status: number, contentType: string, body: string) => void;
type JsonPayload = Record<string, unknown>;
type TagEntry = { tag: string; type: number };
type Identifier = Record<string, string>;
type ImportTranslator = {
  setTranslator(translatorId: string): void;
  setString(input: string): void;
  translate(options: {
    libraryID: number;
    collections: number[];
    saveAttachments: boolean;
  }): Promise<unknown>;
};
type SearchTranslator = {
  setIdentifier(identifier: Identifier): void;
  getTranslators(): Promise<unknown[]>;
  setTranslator(translators: unknown[]): void;
  translate(options: {
    libraryID: number;
    collections: number[] | false;
    saveAttachments: boolean;
  }): Promise<Zotero.Item[]>;
};
type SyncRunner = {
  sync(options: { background: boolean }): Promise<unknown>;
};
type PutContentsAsync = (
  path: string | nsIFile,
  data: string | nsIInputStream | ArrayBuffer | Blob,
  charset?: string,
) => Promise<void>;
type AsyncFunctionConstructor = new (
  ...args: string[]
) => (zotero: typeof Zotero) => Promise<unknown>;
type ActiveZoteroPane = {
  getSelectedCollection(): Zotero.Collection | null;
};

function log(msg: string): void {
  Zotero.debug("Local Write API: " + msg);
}

function sendJSON(sendResponse: SendResponse, statusCode: number, payload: JsonPayload): void {
  sendResponse(statusCode, "application/json", JSON.stringify(payload));
}

function successResult(operation: string, details: JsonPayload, extra?: JsonPayload): JsonPayload {
  const payload: JsonPayload = {
    success: true,
    operation: operation,
    stage: "completed",
    version: PLUGIN_VERSION,
    details: details,
  };
  return extra ? { ...payload, ...extra } : payload;
}

function errorResult(
  operation: string,
  stage: string,
  error: string,
  details: JsonPayload,
): JsonPayload {
  return {
    success: false,
    operation: operation,
    stage: stage,
    error: error,
    details: details,
    version: PLUGIN_VERSION,
  };
}

function pluginVersionPayload(): JsonPayload {
  return {
    success: true,
    healthy: true,
    status: "ok",
    message: "Local Write API is running.",
    version: PLUGIN_VERSION,
    addon_id: ADDON_ID,
    homepage_url: HOMEPAGE_URL,
    update_url: UPDATE_URL,
    endpoints: {
      attach: FULLTEXT_ATTACH_PATH,
      write: LOCAL_WRITE_PATH,
      version: VERSION_PATH,
    },
    compatibility: {
      strict_min_version: STRICT_MIN_VERSION,
      strict_max_version: STRICT_MAX_VERSION,
      tested_zotero_version: TESTED_ZOTERO_VERSION,
    },
    capabilities: PLUGIN_CAPABILITIES.slice(),
  };
}

function requireString(value: unknown, fieldName: string): string {
  if (typeof value !== "string") {
    throw new Error(fieldName + " must be a string");
  }
  return value;
}

function requireNonEmptyString(value: unknown, fieldName: string): string {
  const cleaned = requireString(value, fieldName).trim();
  if (!cleaned) {
    throw new Error(fieldName + " must be a non-empty string");
  }
  return cleaned;
}

function optionalNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const cleaned = value.trim();
  return cleaned ? cleaned : null;
}

function requireObject(value: unknown, fieldName: string): JsonPayload {
  if (!value || Array.isArray(value) || typeof value !== "object") {
    throw new Error(fieldName + " must be an object");
  }
  return value as JsonPayload;
}

function normalizeStringList(value: unknown, fieldName: string): string[] {
  if (!Array.isArray(value)) {
    throw new Error(fieldName + " must be an array of strings");
  }
  const normalized: string[] = [];
  const seen = new Set<string>();
  for (const entry of value) {
    if (typeof entry !== "string") {
      throw new Error(fieldName + " entries must be strings");
    }
    const cleaned = entry.trim();
    if (!cleaned || seen.has(cleaned)) {
      continue;
    }
    normalized.push(cleaned);
    seen.add(cleaned);
  }
  return normalized;
}

function userLibraryID(): number {
  return Zotero.Libraries.userLibraryID;
}

async function getUserItemOrThrow(itemKey: string) {
  const item = Zotero.Items.getByLibraryAndKey(userLibraryID(), itemKey);
  if (!item) {
    throw new Error("Item not found: " + itemKey);
  }
  return item;
}

async function getUserCollectionOrThrow(collectionKey: string) {
  const collection = Zotero.Collections.getByLibraryAndKey(userLibraryID(), collectionKey);
  if (!collection) {
    throw new Error("Collection not found: " + collectionKey);
  }
  return collection;
}

function collectionDetails(collection: Zotero.Collection): JsonPayload {
  // parentKey is the documented `false` sentinel when the collection has no parent;
  // zotero-types models only the `string` case, so read through the real runtime type.
  const parentKey = (collection as { parentKey: string | false }).parentKey;
  return {
    collection_key: collection.key,
    collection_name: collection.name,
    parent_key: parentKey === false ? null : parentKey,
  };
}

async function copyStoredAttachmentFiles(
  sourceAttachment: Zotero.Item,
  newAttachment: Zotero.Item,
): Promise<void> {
  if (!sourceAttachment.isStoredFileAttachment()) {
    return;
  }
  if (!(await sourceAttachment.fileExists())) {
    return;
  }
  const sourceDir = Zotero.Attachments.getStorageDirectory(sourceAttachment);
  const destDir = await Zotero.Attachments.createDirectoryForItem(newAttachment);
  await Zotero.File.copyDirectory(sourceDir, destDir);
}

async function cloneChildAttachmentToParent(
  sourceAttachment: Zotero.Item,
  parentItemID: number,
): Promise<Zotero.Item> {
  const newAttachment = sourceAttachment.clone(sourceAttachment.libraryID);
  newAttachment.parentID = parentItemID;
  await newAttachment.saveTx();
  await copyStoredAttachmentFiles(sourceAttachment, newAttachment);
  return newAttachment;
}

function lexicalFile(filePath: string): nsIFile {
  if (!PathUtils.isAbsolute(filePath)) {
    throw new Error("File path must be absolute: " + filePath);
  }
  const components = PathUtils.split(filePath);
  const fileRoot = Zotero.File.pathToFile(components[0]);
  let file = fileRoot.clone();
  for (const component of components.slice(1)) {
    if (component === ".") {
      continue;
    }
    if (component === "..") {
      if (file.equals(fileRoot)) {
        throw new Error("File path traverses above its root: " + filePath);
      }
      file = file.parent;
      continue;
    }
    file.append(component);
  }
  return file;
}

function resolveAttachFilePath(filePath: string): string {
  const file = lexicalFile(filePath);
  const allowedDirs = FULLTEXT_ALLOWED_DIRS.map((dir) => {
    const allowedDir = Zotero.File.pathToFile(dir);
    allowedDir.normalize();
    return allowedDir;
  });
  const isAllowed = () =>
    allowedDirs.some((allowedDir) => {
      if (allowedDir.equals(file)) {
        return true;
      }
      return allowedDir.contains(file);
    });
  if (!isAllowed()) {
    throw new Error(
      "File path must be within allowed directories: " + FULLTEXT_ALLOWED_DIRS.join(", "),
    );
  }
  if (!file.exists()) {
    throw new Error("File not found: " + file.path);
  }
  file.normalize();
  if (!isAllowed()) {
    throw new Error(
      "File path must be within allowed directories: " + FULLTEXT_ALLOWED_DIRS.join(", "),
    );
  }
  return file.path;
}

function isMissingFileError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }
  if (error.message.startsWith("File not found: ")) {
    return true;
  }
  return error.message.includes("NS_ERROR_FILE_NOT_FOUND");
}

async function materializeUploadBytes(fileName: string, fileBytesBase64: string) {
  const tempDir = Zotero.getTempDirectory();
  const safeFileName = Zotero.File.getValidFileName(fileName.trim());
  if (!safeFileName) {
    throw new Error("File name has no valid characters: " + fileName);
  }
  tempDir.append(
    `local-write-api-${Date.now()}-${Math.random().toString(16).slice(2)}-${safeFileName}`,
  );
  const binary = atob(fileBytesBase64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index++) {
    bytes[index] = binary.charCodeAt(index);
  }
  // Zotero.File.putContentsAsync() accepts Blob at runtime, but zotero-types
  // omits it from the declared input union.
  const putContentsAsync = Zotero.File.putContentsAsync as PutContentsAsync;
  await putContentsAsync(tempDir.path, new Blob([bytes]));
  return tempDir.path;
}

async function importStoredAttachment(
  parentItem: Zotero.Item,
  filePath: string,
  title: string,
): Promise<Zotero.Item> {
  const resolvedFilePath = resolveAttachFilePath(filePath);
  // Copy the file into Zotero's own temp directory before importing.
  // Passing a /tmp path directly causes NS_ERROR_FILE_NOT_FOUND from
  // nsIFile.copyToFollowingLinks when the path resolves through a symlink
  // that Zotero's process cannot follow (observed on Linux tmpfs mounts).
  const sourceFile = Zotero.File.pathToFile(resolvedFilePath);
  const tempDir = Zotero.getTempDirectory();
  const tempName = `local-write-api-${Date.now()}-${sourceFile.leafName}`;
  sourceFile.copyTo(tempDir, tempName);
  const tempFile = tempDir.clone();
  tempFile.append(tempName);
  let attachment: Zotero.Item;
  try {
    const result = await Zotero.Attachments.importFromFile({
      file: tempFile.path,
      libraryID: parentItem.libraryID,
      parentItemID: parentItem.id,
      title: title,
    });
    if (!result) {
      throw new Error("Failed to create attachment");
    }
    await result.saveTx();
    attachment = result;
  } finally {
    if (tempFile.exists()) {
      tempFile.remove(false);
    }
  }
  return attachment;
}

async function handleFulltextAttach(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const title = requireNonEmptyString(data.title, "title");
  const filePath = optionalNonEmptyString(data.file_path);
  const fileName = optionalNonEmptyString(data.file_name);
  const fileBytesBase64 = optionalNonEmptyString(data.file_bytes_base64);

  if (!filePath && !fileBytesBase64) {
    throw new Error("Either file_path or file_bytes_base64 must be provided");
  }

  const parentItem = await getUserItemOrThrow(itemKey);
  let attachment: Zotero.Item;
  let sourceMode = "path";
  let tempPath: string | null = null;

  try {
    if (filePath) {
      try {
        attachment = await importStoredAttachment(parentItem, filePath, title);
      } catch (error) {
        if (!fileBytesBase64 || !isMissingFileError(error)) {
          throw error;
        }
        const fallbackName = fileName ? fileName : Zotero.File.pathToFile(filePath).leafName;
        tempPath = await materializeUploadBytes(fallbackName, fileBytesBase64);
        attachment = await importStoredAttachment(parentItem, tempPath, title);
        sourceMode = "bytes_fallback";
      }
    } else {
      const requiredFileName = requireNonEmptyString(data.file_name, "file_name");
      tempPath = await materializeUploadBytes(
        requiredFileName,
        requireNonEmptyString(data.file_bytes_base64, "file_bytes_base64"),
      );
      attachment = await importStoredAttachment(parentItem, tempPath, title);
      sourceMode = "bytes";
    }
  } finally {
    if (tempPath) {
      try {
        Zotero.File.pathToFile(tempPath).remove(false);
      } catch (error) {
        Zotero.logError(error instanceof Error ? error : new Error(String(error)));
      }
    }
  }

  return successResult(
    "attach_file_to_item",
    {
      parent_item_key: itemKey,
      file_path: filePath,
      source_mode: sourceMode,
      title: title,
    },
    {
      attachment_key: attachment.key,
      attachment_id: attachment.id,
      message: "File attached successfully to item " + itemKey,
      handler: "fulltext-attach",
    },
  );
}

async function handleUpdateItemFields(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const fields = requireObject(data.fields, "fields");
  const item = await getUserItemOrThrow(itemKey);
  item.fromJSON({ ...item.toJSON(), ...fields });
  await item.saveTx();
  return successResult("update_item_fields", {
    item_key: itemKey,
    field_names: Object.keys(fields).sort(),
  });
}

async function handleReplaceItemJSON(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const itemJSON = requireObject(data.item_json, "item_json");
  const item = await getUserItemOrThrow(itemKey);
  item.fromJSON(itemJSON);
  await item.saveTx();
  return successResult("replace_item_json", {
    item_key: itemKey,
    item_type: item.itemType,
  });
}

async function handleSetItemTags(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const tags = normalizeStringList(data.tags, "tags");
  const item = await getUserItemOrThrow(itemKey);
  item.setTags(tags);
  await item.saveTx();
  return successResult("set_item_tags", {
    item_key: itemKey,
    tags: tags,
    tag_count: tags.length,
  });
}

async function handleSetItemCollections(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const collectionKeys = normalizeStringList(data.collection_keys, "collection_keys");
  for (const collectionKey of collectionKeys) {
    await getUserCollectionOrThrow(collectionKey);
  }
  const item = await getUserItemOrThrow(itemKey);
  item.setCollections(collectionKeys);
  await item.saveTx();
  return successResult("set_item_collections", {
    item_key: itemKey,
    collection_keys: collectionKeys,
  });
}

async function handleAttachNote(data: RequestData) {
  const parentItemKey = requireNonEmptyString(data.parent_item_key, "parent_item_key");
  const noteText = requireString(data.note_text, "note_text");
  const parentItem = await getUserItemOrThrow(parentItemKey);

  const noteItem = new Zotero.Item("note");
  noteItem.libraryID = parentItem.libraryID;
  noteItem.parentID = parentItem.id;
  noteItem.setNote(noteText);
  await noteItem.saveTx();

  return successResult(
    "attach_note",
    {
      parent_item_key: parentItemKey,
      note_length: noteText.length,
      title: typeof data.title === "string" ? data.title : null,
    },
    {
      note_key: noteItem.key,
      note_id: noteItem.id,
    },
  );
}

async function handleUpdateNote(data: RequestData) {
  const noteKey = requireNonEmptyString(data.note_key, "note_key");
  const newContent = requireString(data.new_content, "new_content");
  const noteItem = await getUserItemOrThrow(noteKey);
  if (!noteItem.isNote()) {
    throw new Error("Item is not a note: " + noteKey);
  }
  noteItem.setNote(newContent);
  await noteItem.saveTx();

  return successResult("update_note", {
    note_key: noteKey,
    // parentKey is `false`/undefined for a top-level note with no parent item.
    parent_item_key: noteItem.parentKey ? noteItem.parentKey : null,
    content_length: newContent.length,
  });
}

async function handleAttachURL(data: RequestData) {
  const parentItemKey = requireNonEmptyString(data.parent_item_key, "parent_item_key");
  const url = requireNonEmptyString(data.url, "url");
  const parentItem = await getUserItemOrThrow(parentItemKey);
  const title = typeof data.title === "string" && data.title.trim() ? data.title.trim() : null;

  const attachment = await Zotero.Attachments.linkFromURL({
    url: url,
    parentItemID: parentItem.id,
    title: title,
  });

  return successResult(
    "attach_url",
    {
      parent_item_key: parentItemKey,
      url: url,
      // Report the requested title, or the title Zotero auto-assigned when none was given.
      title: title === null ? attachment.getField("title") : title,
    },
    {
      attachment_key: attachment.key,
      attachment_id: attachment.id,
    },
  );
}

async function handleTrashItem(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const item = await getUserItemOrThrow(itemKey);
  item.deleted = true;
  await item.saveTx();
  return successResult("trash_item", {
    item_key: itemKey,
    item_type: item.itemType,
  });
}

async function handleTrashCollection(data: RequestData) {
  const collectionKey = requireNonEmptyString(data.collection_key, "collection_key");
  const collection = await getUserCollectionOrThrow(collectionKey);
  collection.deleted = true;
  await collection.saveTx();
  return successResult("trash_collection", collectionDetails(collection));
}

async function handleRelinkAttachmentFile(data: RequestData) {
  const attachmentKey = requireNonEmptyString(data.attachment_key, "attachment_key");
  const filePath = requireNonEmptyString(data.file_path, "file_path");
  const attachment = await getUserItemOrThrow(attachmentKey);
  if (!attachment.isAttachment()) {
    throw new Error("Item is not an attachment: " + attachmentKey);
  }
  await attachment.relinkAttachmentFile(filePath);
  return successResult("relink_attachment_file", {
    attachment_key: attachmentKey,
    file_path: filePath,
  });
}

async function handleCreateCollection(data: RequestData) {
  const name = requireNonEmptyString(data.name, "name");
  let parentKey: string | null = null;
  if (typeof data.parent_key === "string" && data.parent_key.trim()) {
    parentKey = data.parent_key.trim();
    await getUserCollectionOrThrow(parentKey);
  }

  const collection = new Zotero.Collection({ libraryID: userLibraryID(), name });
  if (parentKey) {
    collection.parentKey = parentKey;
  }
  await collection.saveTx();

  return successResult("create_collection", collectionDetails(collection));
}

async function handleRenameCollection(data: RequestData) {
  const collectionKey = requireNonEmptyString(data.collection_key, "collection_key");
  const newName = requireNonEmptyString(data.new_name, "new_name");
  const collection = await getUserCollectionOrThrow(collectionKey);
  collection.name = newName;
  await collection.saveTx();

  return successResult("rename_collection", collectionDetails(collection));
}

async function handleMoveCollection(data: RequestData) {
  const collectionKey = requireNonEmptyString(data.collection_key, "collection_key");
  const collection = await getUserCollectionOrThrow(collectionKey);
  let newParentKey: string | null = null;
  if (typeof data.new_parent_key === "string" && data.new_parent_key.trim()) {
    newParentKey = data.new_parent_key.trim();
    await getUserCollectionOrThrow(newParentKey);
  }
  // `false` is Zotero's documented "no parent" sentinel when no new parent was given.
  setCollectionParentKey(collection, newParentKey === null ? false : newParentKey);
  await collection.saveTx();

  return successResult("move_collection", collectionDetails(collection));
}

async function handleMergeCollections(data: RequestData) {
  const sourceKeys = normalizeStringList(data.source_keys, "source_keys");
  const targetKey = requireNonEmptyString(data.target_key, "target_key");
  if (sourceKeys.includes(targetKey)) {
    throw new Error("Target collection cannot also be a source collection");
  }
  const targetCollection = await getUserCollectionOrThrow(targetKey);
  let movedItems = 0;
  let movedChildren = 0;
  let trashedSources = 0;

  for (const sourceKey of sourceKeys) {
    const sourceCollection = await getUserCollectionOrThrow(sourceKey);
    const descendents = sourceCollection.getDescendents(false, null, false);
    if (descendents.some((d) => d.type === "collection" && d.key === targetKey)) {
      throw new Error("Cannot merge a collection into one of its descendants");
    }

    const childItems = sourceCollection.getChildItems(true, true);
    if (childItems.length) {
      await targetCollection.addItems(childItems);
      movedItems += childItems.length;
    }

    const childCollections = sourceCollection.getChildCollections(false, true);
    for (const childCollection of childCollections) {
      if (childCollection.key === targetKey) {
        continue;
      }
      childCollection.parentKey = targetKey;
      await childCollection.saveTx();
      movedChildren++;
    }

    sourceCollection.deleted = true;
    await sourceCollection.saveTx();
    trashedSources++;
  }

  return successResult("merge_collections", {
    source_keys: sourceKeys,
    target_key: targetKey,
    moved_item_count: movedItems,
    moved_child_collection_count: movedChildren,
    trashed_source_count: trashedSources,
  });
}

async function handleRenameTag(data: RequestData) {
  const oldName = requireNonEmptyString(data.old_name, "old_name");
  const newName = requireNonEmptyString(data.new_name, "new_name");
  await Zotero.Tags.rename(userLibraryID(), oldName, newName);
  return successResult("rename_tag", {
    old_name: oldName,
    new_name: newName,
  });
}

async function handleMergeTags(data: RequestData) {
  const sourceTags = normalizeStringList(data.source_tags, "source_tags");
  const targetTag = requireNonEmptyString(data.target_tag, "target_tag");
  for (const sourceTag of sourceTags) {
    if (sourceTag === targetTag) {
      continue;
    }
    await Zotero.Tags.rename(userLibraryID(), sourceTag, targetTag);
  }
  return successResult("merge_tags", {
    source_tags: sourceTags,
    target_tag: targetTag,
  });
}

async function handleDeleteTag(data: RequestData) {
  const tagName = requireNonEmptyString(data.tag_name, "tag_name");
  const tagID = Zotero.Tags.getID(tagName);
  if (!tagID) {
    throw new Error("Tag not found: " + tagName);
  }

  // Remove the tag from every item that carries it before removing it from the
  // library, and report how many items changed.
  const search = new Zotero.Search({ libraryID: userLibraryID() });
  search.addCondition("tag", "is", tagName);
  const itemIDs = await search.search();

  let modifiedCount = 0;
  if (itemIDs && itemIDs.length > 0) {
    const items = await Zotero.Items.getAsync(itemIDs);
    for (const item of items) {
      if (item.removeTag(tagName)) {
        await item.saveTx();
        modifiedCount++;
      }
    }
  }

  await removeTagsFromUserLibrary(userLibraryID(), [tagID]);

  return successResult("delete_tag", {
    tag_name: tagName,
    modified_item_count: modifiedCount,
  });
}

async function handleDeleteUnusedTags(_data: RequestData) {
  Zotero.Prefs.set("purge.tags", true);
  await Zotero.DB.executeTransaction(async function () {
    await Zotero.Tags.purge();
  });
  return successResult("delete_unused_tags", {});
}

async function handleCopyItem(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const original = await getUserItemOrThrow(itemKey);
  const newItem = original.clone(original.libraryID, { includeCollections: true });
  if (newItem.isRegularItem()) {
    const currentTitle = newItem.getField("title");
    if (currentTitle) {
      newItem.setField("title", currentTitle + " (copy)");
    }
  }
  // saveTx() returns number | boolean in zotero-types; for a new item it is always the numeric ID
  const newItemID = (await newItem.saveTx()) as number;
  const newItemKey = newItem.key;
  let copiedNotes = 0;
  let copiedAttachments = 0;

  if (original.isAttachment()) {
    await copyStoredAttachmentFiles(original, newItem);
  }

  if (original.isRegularItem()) {
    const noteIDs = original.getNotes(true);
    for (const note of Zotero.Items.get(noteIDs)) {
      const newNote = note.clone(original.libraryID);
      newNote.parentID = newItemID;
      await newNote.saveTx();
      copiedNotes++;
    }

    const attachmentIDs = original.getAttachments(true);
    for (const attachment of Zotero.Items.get(attachmentIDs)) {
      await cloneChildAttachmentToParent(attachment, newItemID);
      copiedAttachments++;
    }
  }

  return successResult(
    "copy_item",
    {
      item_key: itemKey,
      copied_note_count: copiedNotes,
      copied_attachment_count: copiedAttachments,
    },
    {
      new_key: newItemKey,
      new_item_key: newItemKey,
    },
  );
}

async function handleMergeItems(data: RequestData) {
  const sourceKey = requireNonEmptyString(data.source_key, "source_key");
  const targetKey = requireNonEmptyString(data.target_key, "target_key");
  if (sourceKey === targetKey) {
    throw new Error("Source and target items must be different");
  }

  const sourceItem = await getUserItemOrThrow(sourceKey);
  const targetItem = await getUserItemOrThrow(targetKey);
  if (!sourceItem.isRegularItem() || !targetItem.isRegularItem()) {
    throw new Error("merge_items requires two regular Zotero items");
  }
  const transferred = {
    attachments: 0,
    notes: 0,
    tags: 0,
    relations: 0,
  };

  const sourceTags = sourceItem.getTags() as TagEntry[];
  const targetTags = targetItem.getTags() as TagEntry[];
  const targetTagNames = new Set(targetTags.map((tag) => tag.tag));
  for (const tag of sourceTags) {
    if (!targetTagNames.has(tag.tag)) {
      targetTags.push(tag);
      targetTagNames.add(tag.tag);
      transferred.tags++;
    }
  }
  targetItem.setTags(targetTags);

  const sourceRelations = sourceItem.getRelations();
  let targetRelations = targetItem.getRelations();
  for (const [predicate, sourceValues] of Object.entries(sourceRelations)) {
    const key = predicate as _ZoteroTypes.RelationsPredicate;
    const targetValues = targetRelations[key] ? [...targetRelations[key]] : [];
    const targetValueSet = new Set(targetValues);
    for (const value of sourceValues) {
      if (!targetValueSet.has(value)) {
        targetValues.push(value);
        targetValueSet.add(value);
        transferred.relations++;
      }
    }
    targetItem.setRelations({ ...targetRelations, [key]: targetValues });
    targetRelations = targetItem.getRelations();
  }
  await targetItem.saveTx();

  for (const note of Zotero.Items.get(sourceItem.getNotes(true))) {
    note.parentID = targetItem.id;
    await note.saveTx();
    transferred.notes++;
  }
  for (const attachment of Zotero.Items.get(sourceItem.getAttachments(true))) {
    attachment.parentID = targetItem.id;
    await attachment.saveTx();
    transferred.attachments++;
  }

  sourceItem.deleted = true;
  await sourceItem.saveTx();

  return successResult("merge_items", {
    source_key: sourceKey,
    target_key: targetKey,
    transferred: transferred,
  });
}

async function handleCreateItem(data: RequestData) {
  const itemType = requireNonEmptyString(data.item_type, "item_type");
  const fields = data.fields ? requireObject(data.fields, "fields") : {};
  const tags = data.tags ? normalizeStringList(data.tags, "tags") : [];
  const collectionKeys = data.collection_keys
    ? normalizeStringList(data.collection_keys, "collection_keys")
    : [];

  for (const collectionKey of collectionKeys) {
    await getUserCollectionOrThrow(collectionKey);
  }

  // itemType is a user-supplied item-type name; Zotero validates it at runtime and
  // throws on an unknown type. The constructor types the name as a literal union, so
  // narrow the runtime string to that union (a no-op at runtime).
  const item = new Zotero.Item(
    itemType as _ZoteroTypes.Item.ItemTypeMapping[keyof _ZoteroTypes.Item.ItemTypeMapping],
  );
  item.libraryID = userLibraryID();

  item.fromJSON({ ...item.toJSON(), ...fields });

  if (tags.length) {
    item.setTags(tags);
  }
  if (collectionKeys.length) {
    item.setCollections(collectionKeys);
  }

  await item.saveTx();

  return successResult(
    "create_item",
    {
      item_type: itemType,
      field_names: Object.keys(fields).sort(),
      tag_count: tags.length,
      collection_count: collectionKeys.length,
    },
    {
      item_key: item.key,
      item_id: item.id,
    },
  );
}

async function handleAddItemTags(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const tagsToAdd = normalizeStringList(data.tags, "tags");
  const item = await getUserItemOrThrow(itemKey);
  const existing = item.getTags() as TagEntry[];
  const existingNames = new Set(existing.map((t) => t.tag));
  const added: string[] = [];
  for (const tag of tagsToAdd) {
    if (!existingNames.has(tag)) {
      existing.push({ tag: tag, type: 0 });
      existingNames.add(tag);
      added.push(tag);
    }
  }
  item.setTags(existing);
  await item.saveTx();
  return successResult("add_item_tags", {
    item_key: itemKey,
    added_tags: added,
    total_tag_count: existing.length,
  });
}

async function handleRemoveItemTags(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const tagsToRemove = new Set(normalizeStringList(data.tags, "tags"));
  const item = await getUserItemOrThrow(itemKey);
  const allTags = item.getTags() as TagEntry[];
  const removedCount = allTags.filter((t) => tagsToRemove.has(t.tag)).length;
  const filtered = allTags.filter((t) => !tagsToRemove.has(t.tag));
  item.setTags(filtered);
  await item.saveTx();
  return successResult("remove_item_tags", {
    item_key: itemKey,
    removed_count: removedCount,
    remaining_tag_count: filtered.length,
  });
}

async function handleAddItemToCollection(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const collectionKey = requireNonEmptyString(data.collection_key, "collection_key");
  const item = await getUserItemOrThrow(itemKey);
  const collection = await getUserCollectionOrThrow(collectionKey);
  const currentKeys = item.getCollections().map((id) => Zotero.Collections.get(id).key);
  if (!currentKeys.includes(collectionKey)) {
    item.setCollections([...currentKeys, collectionKey]);
    await item.saveTx();
  }
  return successResult("add_item_to_collection", {
    item_key: itemKey,
    collection_key: collectionKey,
    collection_name: collection.name,
  });
}

async function handleRemoveItemFromCollection(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const collectionKey = requireNonEmptyString(data.collection_key, "collection_key");
  const item = await getUserItemOrThrow(itemKey);
  const collection = await getUserCollectionOrThrow(collectionKey);
  const currentKeys = item
    .getCollections()
    .map((id) => Zotero.Collections.get(id).key)
    .filter((k) => k !== collectionKey);
  item.setCollections(currentKeys);
  await item.saveTx();
  return successResult("remove_item_from_collection", {
    item_key: itemKey,
    collection_key: collectionKey,
    collection_name: collection.name,
  });
}

function extractIdentifiers(raw: string): Identifier[] {
  const utilities = Zotero.Utilities as typeof Zotero.Utilities & {
    extractIdentifiers(identifier: string): Identifier[];
  };
  const identifiers = utilities.extractIdentifiers(raw);
  if (!identifiers.length) {
    throw new Error("Could not parse identifier");
  }
  return identifiers;
}

function createImportTranslator(): ImportTranslator {
  const translateApi = Zotero.Translate as {
    Import: new () => ImportTranslator;
  };
  return new translateApi.Import();
}

function createSearchTranslator(): SearchTranslator {
  const translateApi = Zotero.Translate as {
    Search: new () => SearchTranslator;
  };
  return new translateApi.Search();
}

function requireImportedItems(value: unknown, operation: string): Zotero.Item[] {
  if (!Array.isArray(value)) {
    throw new Error(operation + " did not return an item array");
  }
  for (const item of value) {
    if (typeof item !== "object" || item === null) {
      throw new Error(operation + " returned a non-object item");
    }
    const candidate = item as { key?: unknown; id?: unknown };
    if (typeof candidate.key !== "string" || typeof candidate.id !== "number") {
      throw new Error(operation + " returned an item without key/id");
    }
  }
  return value as Zotero.Item[];
}

async function handleImportBibTeX(data: RequestData) {
  const bibtex = requireNonEmptyString(data.bibtex, "bibtex");
  const collectionKeys = data.collection_keys
    ? normalizeStringList(data.collection_keys, "collection_keys")
    : [];
  const collectionIDs: number[] = [];
  for (const collectionKey of collectionKeys) {
    const collection = await getUserCollectionOrThrow(collectionKey);
    collectionIDs.push(collection.id);
  }

  const translator = createImportTranslator();
  translator.setTranslator(BIBTEX_TRANSLATOR_ID);
  translator.setString(bibtex);
  const items = requireImportedItems(
    await translator.translate({
      libraryID: userLibraryID(),
      collections: collectionIDs,
      saveAttachments: true,
    }),
    "import_bibtex",
  );
  if (items.length !== 1) {
    throw new Error("import_bibtex must create exactly one Zotero item");
  }

  return successResult(
    "import_bibtex",
    {
      item_count: items.length,
      collection_keys: collectionKeys,
      translator_id: BIBTEX_TRANSLATOR_ID,
    },
    {
      item_key: items[0].key,
      item_id: items[0].id,
      item_keys: items.map((item) => item.key),
      item_ids: items.map((item) => item.id),
      titles: items.map((item) => item.getField("title")),
    },
  );
}

async function translateIdentifier(
  identifier: Identifier,
  collections: number[] | false,
): Promise<Zotero.Item[]> {
  const search = createSearchTranslator();
  search.setIdentifier(identifier);
  const translators = await search.getTranslators();
  if (!translators || translators.length === 0) {
    throw new Error("No translator available for identifier: " + JSON.stringify(identifier));
  }
  search.setTranslator(translators);
  const items = await search.translate({
    libraryID: userLibraryID(),
    collections: collections,
    saveAttachments: true,
  });
  if (!items || items.length === 0) {
    throw new Error("No item found for identifier: " + JSON.stringify(identifier));
  }
  return items;
}

async function handleImportByIdentifier(data: RequestData) {
  const raw = requireNonEmptyString(data.identifier, "identifier");
  const collectionKeys = data.collection_keys
    ? normalizeStringList(data.collection_keys, "collection_keys")
    : [];
  const collections: number[] = [];
  for (const collectionKey of collectionKeys) {
    const collection = await getUserCollectionOrThrow(collectionKey);
    collections.push(collection.id);
  }

  const items: Zotero.Item[] = [];
  for (const identifier of extractIdentifiers(raw)) {
    items.push(...(await translateIdentifier(identifier, collections)));
  }

  return successResult(
    "import_by_identifier",
    {
      identifier: raw,
      item_count: items.length,
      collection_keys: collectionKeys,
    },
    {
      item_key: items[0].key,
      item_id: items[0].id,
      item_keys: items.map((item) => item.key),
      item_ids: items.map((item) => item.id),
      titles: items.map((item) => item.getField("title")),
    },
  );
}

function handleGetSelectedCollection(): JsonPayload {
  const pane = Zotero.getActiveZoteroPane() as ActiveZoteroPane;
  const collection = pane.getSelectedCollection();
  if (!collection) {
    throw new Error("No Collection selected.");
  }
  return successResult("get_selected_collection", {
    collection_key: collection.key,
    collection_name: collection.name,
  });
}

async function handleRestoreItem(data: RequestData) {
  const itemKey = requireNonEmptyString(data.item_key, "item_key");
  const item = await getUserItemOrThrow(itemKey);
  item.deleted = false;
  await item.saveTx();
  return successResult("restore_item", {
    item_key: itemKey,
    item_type: item.itemType,
  });
}

async function handleUpdateAttachmentTitle(data: RequestData) {
  const attachmentKey = requireNonEmptyString(data.attachment_key, "attachment_key");
  const newTitle = requireNonEmptyString(data.new_title, "new_title");
  const attachment = await getUserItemOrThrow(attachmentKey);
  if (!attachment.isAttachment()) {
    throw new Error("Item is not an attachment: " + attachmentKey);
  }
  attachment.setField("title", newTitle);
  await attachment.saveTx();
  return successResult("update_attachment_title", {
    attachment_key: attachmentKey,
    new_title: newTitle,
  });
}

function serializeResult(result: unknown): unknown {
  return result === undefined ? null : JSON.parse(JSON.stringify(result));
}

async function handleSync(data: RequestData) {
  void data;
  const syncApi = Zotero.Sync as { Runner?: SyncRunner };
  const runner = syncApi.Runner;
  if (!runner) {
    throw new Error("Zotero.Sync.Runner.sync is unavailable");
  }
  // Foreground sync so the call resolves once the sync engine has run.
  const result = await runner.sync({ background: false });
  return successResult("sync", { triggered: true, result: serializeResult(result) });
}

function createAsyncFunction(code: string): (zotero: typeof Zotero) => Promise<unknown> {
  const prototype = Object.getPrototypeOf(async function () {}) as object;
  const descriptor: PropertyDescriptor | undefined = Object.getOwnPropertyDescriptor(
    prototype,
    "constructor",
  );
  const constructor: unknown = descriptor?.value;
  if (typeof constructor !== "function") {
    throw new Error("AsyncFunction constructor is unavailable");
  }
  const AsyncFunction = constructor as AsyncFunctionConstructor;
  return new AsyncFunction("Zotero", code);
}

async function handleRunJavascript(data: RequestData) {
  // Debug endpoint: evaluate arbitrary internal JavaScript in the add-on's privileged
  // chrome scope, with `Zotero` in scope and `await` supported. Single-user dev tool.
  const code = requireNonEmptyString(data.code, "code");
  const result = await createAsyncFunction(code)(Zotero);
  return successResult("run_javascript", { result: serializeResult(result) });
}

async function runWrite(data: RequestData) {
  const operation = requireNonEmptyString(data.operation, "operation");
  switch (operation) {
    case "sync":
      return handleSync(data);
    case "run_javascript":
      return handleRunJavascript(data);
    case "update_item_fields":
      return handleUpdateItemFields(data);
    case "replace_item_json":
      return handleReplaceItemJSON(data);
    case "set_item_tags":
      return handleSetItemTags(data);
    case "add_item_tags":
      return handleAddItemTags(data);
    case "remove_item_tags":
      return handleRemoveItemTags(data);
    case "set_item_collections":
      return handleSetItemCollections(data);
    case "add_item_to_collection":
      return handleAddItemToCollection(data);
    case "remove_item_from_collection":
      return handleRemoveItemFromCollection(data);
    case "attach_note":
      return handleAttachNote(data);
    case "update_note":
      return handleUpdateNote(data);
    case "attach_url":
      return handleAttachURL(data);
    case "trash_item":
      return handleTrashItem(data);
    case "trash_collection":
      return handleTrashCollection(data);
    case "relink_attachment_file":
      return handleRelinkAttachmentFile(data);
    case "create_collection":
      return handleCreateCollection(data);
    case "rename_collection":
      return handleRenameCollection(data);
    case "move_collection":
      return handleMoveCollection(data);
    case "merge_collections":
      return handleMergeCollections(data);
    case "rename_tag":
      return handleRenameTag(data);
    case "merge_tags":
      return handleMergeTags(data);
    case "delete_tag":
      return handleDeleteTag(data);
    case "delete_unused_tags":
      return handleDeleteUnusedTags(data);
    case "copy_item":
      return handleCopyItem(data);
    case "merge_items":
      return handleMergeItems(data);
    case "create_item":
      return handleCreateItem(data);
    case "import_bibtex":
      return handleImportBibTeX(data);
    case "import_by_identifier":
      return handleImportByIdentifier(data);
    case "get_selected_collection":
      return handleGetSelectedCollection();
    case "restore_item":
      return handleRestoreItem(data);
    case "update_attachment_title":
      return handleUpdateAttachmentTitle(data);
    default:
      throw new Error("Unsupported operation: " + operation);
  }
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function install(): void {
  log("Installed " + PLUGIN_VERSION);
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function startup({
  id,
  version,
  rootURI,
}: {
  id: string;
  version: string;
  rootURI: string;
}): Promise<void> {
  void id;
  void version;
  void rootURI;
  log("Starting " + PLUGIN_VERSION);

  AttachEndpoint = function () {};
  AttachEndpoint.prototype = {
    supportedMethods: ["POST"],
    supportedDataTypes: ["application/json"],
    init: async function (data: RequestData, sendResponse: SendResponse) {
      try {
        log("Received POST request to " + FULLTEXT_ATTACH_PATH + " [v" + PLUGIN_VERSION + "]");
        sendJSON(sendResponse, 200, await handleFulltextAttach(data));
      } catch (error) {
        const msg = (error as Error).message;
        log("Error in " + FULLTEXT_ATTACH_PATH + " [v" + PLUGIN_VERSION + "]: " + msg);
        sendJSON(
          sendResponse,
          500,
          errorResult("attach_file_to_item", "attach_endpoint", msg, { request: data }),
        );
      }
    },
  };

  WriteEndpoint = function () {};
  WriteEndpoint.prototype = {
    supportedMethods: ["POST"],
    supportedDataTypes: ["application/json"],
    init: async function (data: RequestData, sendResponse: SendResponse) {
      // operation may be absent on a malformed request; label it explicitly for
      // diagnostics. This is the error-rendering boundary, not a runtime default.
      const operationLabel = typeof data.operation === "string" ? data.operation : "unknown_operation";
      try {
        log("Received POST request to " + LOCAL_WRITE_PATH + " [operation=" + operationLabel + "]");
        sendJSON(sendResponse, 200, await runWrite(data));
      } catch (error) {
        const msg = (error as Error).message;
        log("Error in " + LOCAL_WRITE_PATH + " [operation=" + operationLabel + "]: " + msg);
        sendJSON(
          sendResponse,
          500,
          errorResult(operationLabel, "write_endpoint", msg, { request: data }),
        );
      }
    },
  };

  VersionEndpoint = function () {};
  VersionEndpoint.prototype = {
    supportedMethods: ["GET"],
    init: function (_data: unknown, sendResponse: SendResponse) {
      log("Received GET request to " + VERSION_PATH + " [v" + PLUGIN_VERSION + "]");
      sendJSON(sendResponse, 200, pluginVersionPayload());
    },
  };

  Zotero.Server.Endpoints[FULLTEXT_ATTACH_PATH] = AttachEndpoint;
  Zotero.Server.Endpoints[LOCAL_WRITE_PATH] = WriteEndpoint;
  Zotero.Server.Endpoints[VERSION_PATH] = VersionEndpoint;
  log("Registered " + FULLTEXT_ATTACH_PATH + " endpoint");
  log("Registered " + LOCAL_WRITE_PATH + " endpoint");
  log("Registered " + VERSION_PATH + " endpoint");
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function onMainWindowLoad({ window: _window }: { window: Window }): void {
  // No window modifications needed
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function onMainWindowUnload({ window: _window }: { window: Window }): void {
  // No window modifications needed
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function shutdown(
  { id, version, rootURI }: { id: string; version: string; rootURI: string },
  reason: number,
): void {
  void id;
  void version;
  void rootURI;
  if (reason === APP_SHUTDOWN) return;
  log("Shutting down " + PLUGIN_VERSION);
  delete Zotero.Server.Endpoints[FULLTEXT_ATTACH_PATH];
  delete Zotero.Server.Endpoints[LOCAL_WRITE_PATH];
  delete Zotero.Server.Endpoints[VERSION_PATH];
  AttachEndpoint = undefined;
  WriteEndpoint = undefined;
  VersionEndpoint = undefined;
  log("Unregistered " + FULLTEXT_ATTACH_PATH + " endpoint");
  log("Unregistered " + LOCAL_WRITE_PATH + " endpoint");
  log("Unregistered " + VERSION_PATH + " endpoint");
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function uninstall(): void {
  log("Uninstalled " + PLUGIN_VERSION);
}
