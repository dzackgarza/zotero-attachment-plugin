import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { YAML } from "bun";

type Schema = {
  allOf?: Schema[];
  anyOf?: Array<{ $ref: string }>;
  discriminator?: { mapping: Record<string, string> };
  oneOf?: Array<{ $ref: string }>;
  properties?: Record<string, Schema & { enum?: string[] }>;
  required?: string[];
};

type OpenAPI = {
  info: { version: string };
  paths: Record<string, unknown>;
  components: { schemas: Record<string, Schema> };
};

type Config = { endpoints: Record<string, string> };

function parseYaml<T>(path: string): T {
  return YAML.parse(readFileSync(path, "utf8")) as T;
}

function writeOperations(): string[] {
  let source = ts.createSourceFile(
    "src/bootstrap.ts",
    readFileSync("src/bootstrap.ts", "utf8"),
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS,
  );
  let operations: string[] = [];

  function visit(node: ts.Node): void {
    if (ts.isFunctionDeclaration(node) && node.name?.text === "runWrite") {
      function collectCases(child: ts.Node): void {
        if (ts.isCaseClause(child) && ts.isStringLiteral(child.expression)) {
          operations.push(child.expression.text);
        }
        ts.forEachChild(child, collectCases);
      }
      collectCases(node);
      return;
    }
    ts.forEachChild(node, visit);
  }

  visit(source);
  return operations.sort();
}

test("OpenAPI contract tracks runtime metadata and every write operation", () => {
  let spec = parseYaml<OpenAPI>("openapi.yaml");
  let config = parseYaml<Config>("config.yml");
  let version = readFileSync("VERSION", "utf8").trim();
  let writeRequest = spec.components.schemas.WriteRequest;
  let runtimeOperations = writeOperations();

  expect(spec.info.version).toBe(version);
  expect(Object.keys(spec.paths).sort()).toEqual(Object.values(config.endpoints).sort());
  expect(Object.keys(writeRequest.discriminator!.mapping).sort()).toEqual(runtimeOperations);
  expect(
    writeRequest.oneOf!.map((entry) => entry.$ref).sort(),
  ).toEqual(Object.values(writeRequest.discriminator!.mapping).sort());

  for (let [operation, reference] of Object.entries(writeRequest.discriminator!.mapping)) {
    let schemaName = reference.split("/").at(-1)!;
    let operationSchema = spec.components.schemas[schemaName];
    expect(operationSchema.required).toContain("operation");
    expect(operationSchema.properties!.operation.enum).toEqual([operation]);
  }
});

test("OpenAPI contract marks guaranteed response fields as required", () => {
  let schemas = parseYaml<OpenAPI>("openapi.yaml").components.schemas;

  expect(schemas.SuccessEnvelope.required).toEqual([
    "success",
    "operation",
    "stage",
    "version",
    "details",
  ]);
  expect(schemas.AttachSuccessResponse.allOf?.[1].required).toEqual([
    "attachment_key",
    "attachment_id",
    "message",
    "handler",
  ]);
  expect(schemas.VersionResponse.properties!.endpoints.required).toEqual([
    "attach",
    "write",
    "version",
  ]);
  expect(schemas.VersionResponse.properties!.compatibility.required).toEqual([
    "strict_min_version",
    "strict_max_version",
    "tested_zotero_version",
  ]);
});

test("attachment contract accepts path requests with byte fallback", () => {
  let attachRequest = parseYaml<OpenAPI>("openapi.yaml").components.schemas.AttachRequest;

  expect(attachRequest.oneOf).toBeUndefined();
  expect(attachRequest.anyOf).toEqual([
    { $ref: "#/components/schemas/AttachByPath" },
    { $ref: "#/components/schemas/AttachByBytes" },
  ]);
});
