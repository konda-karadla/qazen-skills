# Business Requirements Document — QAZen Demo Shop

**Document type:** BRD  
**Project:** QAZen Phase 1 vertical-slice demo  
**Targets:** UI — https://www.saucedemo.com ; API — https://reqres.in  
**Notes:** Public demo sites only. Do not use real customer PII. Credentials below are the site’s published demo accounts.

---

## 1. Purpose

Validate that the demo e-commerce storefront accepts authentication correctly, exposes an inventory catalog after login, supports adding a product to the cart, and that the companion user directory API returns contract-valid responses for list, get-by-id, and create operations.

---

## 2. Scope

### In scope
- UI login (valid and invalid credentials)
- UI inventory visibility after successful login
- UI add-to-cart happy path for a single product
- API list users (paginated)
- API get user by id
- API create user

### Out of scope
- Payment / checkout completion
- Database validation
- Production environments
- Visual regression / accessibility scanning

---

## 3. UI requirements — Sauce Demo (https://www.saucedemo.com)

### UR-1 Login with valid credentials
- **Given** a user is on the login page  
- **When** they enter username `standard_user` and password `secret_sauce` and submit  
- **Then** they are taken to the inventory page (URL contains `/inventory.html`)  
- **And** the inventory product list is visible

### UR-2 Login with invalid credentials
- **Given** a user is on the login page  
- **When** they enter an unrecognized username/password combination and submit  
- **Then** they remain on the login page  
- **And** an error message is displayed indicating credentials are invalid

### UR-3 Inventory visibility after login
- **Given** a user has successfully logged in as `standard_user`  
- **When** the inventory page is shown  
- **Then** at least one product item is listed  
- **And** each listed product shows a name and an “Add to cart” control

### UR-4 Add product to cart (happy path)
- **Given** a logged-in `standard_user` on the inventory page  
- **When** they click “Add to cart” for the product named “Sauce Labs Backpack”  
- **Then** the cart badge shows a count of `1`  
- **And** the control for that product changes to indicate the item was added (e.g. “Remove”)

---

## 4. API requirements — ReqRes (https://reqres.in)

Base URL: `https://reqres.in/api`

### AR-1 List users (page 2)
- **When** the client sends `GET /users?page=2`  
- **Then** the response status code is `200`  
- **And** the JSON body includes a `data` array of user objects  
- **And** each user object includes `id`, `email`, `first_name`, `last_name`

### AR-2 Get user by id
- **When** the client sends `GET /users/2`  
- **Then** the response status code is `200`  
- **And** the JSON body `data.id` equals `2`  
- **And** `data.email` is a non-empty string

### AR-3 Create user
- **When** the client sends `POST /users` with JSON body `{"name": "morpheus", "job": "leader"}`  
- **Then** the response status code is `201`  
- **And** the JSON body includes `id` and `createdAt`  
- **And** `name` equals `morpheus` and `job` equals `leader`

---

## 5. Business rules referenced

| ID | Rule | Status in this BRD |
|----|------|--------------------|
| BR-AUTH-01 | Only published demo credentials are valid for Sauce Demo login | Explicit |
| BR-CART-01 | Cart badge count increments by 1 when a single distinct product is added | Explicit |
| BR-API-01 | ReqRes list/get endpoints return HTTP 200 on success; create returns HTTP 201 | Explicit |
| BR-ENV-01 | All automation runs against non-production public demo hosts only | Explicit |

---

## 6. Acceptance criteria (summary)

1. Valid Sauce Demo login lands on inventory with visible products.  
2. Invalid Sauce Demo login shows an error and does not enter inventory.  
3. Adding Sauce Labs Backpack updates the cart badge to 1.  
4. `GET /api/users?page=2` returns 200 with a `data` array.  
5. `GET /api/users/2` returns 200 with `data.id == 2`.  
6. `POST /api/users` with name/job returns 201 with `id` and `createdAt`.

---

## 7. Test data notes

- UI credentials: use only Sauce Demo’s published accounts (`standard_user` / `secret_sauce`).  
- Invalid login: any non-matching pair (e.g. `locked_out_user` with wrong password, or `invalid_user` / `wrong_pass`).  
- API payloads: synthetic only; no production PII.
