# Postman tests (API validation)

This guide explains how to validate the API via Postman using environment variables and simple test scripts.

## Preconditions

- API is running locally:
  - Swagger: `http://localhost:8000/api/doc/`
  - Base API: `http://localhost:8000/api/`
- Database is available (Docker compose or local PostgreSQL).

## Environment variables

Use the ready-made files under `postman/`:

- `postman/TestPrj_Local.postman_environment.json`
- `postman/TestPrj_API.postman_collection.json`

Import them in Postman (File → Import → Upload Files). The environment already contains:

- `base_url` – `http://localhost:8000/api`
- `bs4_url` – a sample product URL
- `search_query` – `Apple iPhone 15 128GB Black`
- `product_id` – pre-created but empty (tests will fill it)

## Requests covered by the collection

The collection (`TestPrj API`) contains the following sequence:

### 1) Health / Docs

(Optional)

- `GET {{base_url}}/products/`

Tests:

```javascript
pm.test("status 200", function () {
  pm.response.to.have.status(200);
});
```

### 2) Scrape (bs4)

- `POST {{base_url}}/products/scrape/bs4/`
- Body (raw JSON):

```json
{
  "url": "{{bs4_url}}"
}
```

Tests:

```javascript
pm.test("status 200 or 201", function () {
  pm.expect([200, 201]).to.include(pm.response.code);
});

const json = pm.response.json();
pm.expect(json).to.have.property("id");
pm.environment.set("product_id", json.id);

pm.test("has required fields", function () {
  pm.expect(json).to.have.property("product_code");
  pm.expect(json).to.have.property("source_url");
  pm.expect(json).to.have.property("price");
});
```

### 3) Scrape (selenium)

- `POST {{base_url}}/products/scrape/selenium/`
- Body (raw JSON):

```json
{
  "query": "{{search_query}}"
}
```

Tests:

```javascript
pm.test("status 200 or 201", function () {
  pm.expect([200, 201]).to.include(pm.response.code);
});

const json = pm.response.json();
pm.expect(json).to.have.property("id");
pm.environment.set("product_id", json.id);
```

### 4) Scrape (playwright)

- `POST {{base_url}}/products/scrape/playwright/`
- Body (raw JSON):

```json
{
  "query": "{{search_query}}"
}
```

Tests:

```javascript
pm.test("status 200 or 201", function () {
  pm.expect([200, 201]).to.include(pm.response.code);
});

const json = pm.response.json();
pm.expect(json).to.have.property("id");
pm.environment.set("product_id", json.id);
```

### 5) Get product by id

- `GET {{base_url}}/products/{{product_id}}/`

Tests:

```javascript
pm.test("status 200", function () {
  pm.response.to.have.status(200);
});

const json = pm.response.json();
pm.expect(json).to.have.property("id");
pm.expect(String(json.id)).to.equal(String(pm.environment.get("product_id")));
```

### 6) Export CSV

- `GET {{base_url}}/products/export-csv/`

Tests:

```javascript
pm.test("status 200", function () {
  pm.response.to.have.status(200);
});

pm.test("content-type looks like csv", function () {
  const ct = pm.response.headers.get("Content-Type") || "";
  pm.expect(ct.toLowerCase()).to.include("text/csv");
});
```

## Validation of input rules (negative tests)

### bs4 forbids query

- `POST {{base_url}}/products/scrape/bs4/`

```json
{
  "query": "{{search_query}}"
}
```

Expected: `400`.

### selenium/playwright require query

- `POST {{base_url}}/products/scrape/selenium/`

```json
{
  "url": "{{bs4_url}}"
}
```

Expected: `400`.

## Running the collection

### Postman UI

- Select the environment (`TestPrj Local`)
- Click **Run collection**
- Run sequentially (recommended)

### Newman (CLI)

```bash
npm install -g newman
newman run postman/TestPrj_API.postman_collection.json \
  -e postman/TestPrj_Local.postman_environment.json
```

## Notes

- Selenium/Playwright scraping depends on installed browser/drivers on the machine that runs the API.
- If you run the API inside Docker without Selenium/Playwright dependencies, prefer `bs4` for smoke checks.
