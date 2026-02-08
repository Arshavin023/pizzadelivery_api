# pizzadelivery_api
# 🛒 eCommerce Platform API

This repository contains a robust and scalable RESTful API for an eCommerce platform designed to serve a large customer base. It includes features like user authentication, order processing, product management, cart handling, and admin reporting.

---

## 🚀 Features

- **Secure Authentication and Role-based Authorization**
- **Product, Order, and Inventory Management**
- **Cart and Checkout Workflows**
- **User Profile and Address Handling**
- **Payments Integration**
- **Customer Reviews and Ratings**
- **Real-time Notifications**
- **Admin Reporting Dashboard**

---

## 📦 Tech Stack

- **Backend:** FastAPI 
- **Database:** PostgreSQL
- **Authentication:** JWT Tokens
- **ORM:** SQLAlchemy 
- **Dev Tools:** Swagger, Git, VSCode, Linux

---

## 📚 API Endpoints Overview

### 1. 🔐 Authentication & Authorization

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register` | POST | User Registration |
| `/login` | POST | User Login |
| `/refresh` | POST | Refresh JWT Token |
| `/logout` | POST | User Logout |
| `/roles` | GET | Get Roles (Admin) |
| `/assign-role` | POST | Assign Role to User (Admin) |

---

### 2. 👤 User Profile & Address

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/profile/retrieve` | GET | Get User Profile |
| `/api/users/profiles` | GET | Get All User Profiles|
| `/api/users/update_biodata/` | PUT | Update User Information |
| `/api/users/update_address` | PUT | Update User Address  |

---

### 3. 🗂️ Category & Inventory

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/categories/create` | POST | Create Category (Admin) |
| `/api/categories/retrieve/{category_id}` | GET | Get Category |
| `/api/categories/categories` | GET | Get Categories |
| `/api/categories/update/{category_id}` | PUT | Update Category (Admin) |
| `/api/categories/delete/{category_id}` | DELETE | Delete Category (Admin) |
| `/inventory/{product_id}` | PUT | Update Inventory (Admin) |

---

### 4. 🛍️ Product Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/products/products` | GET | List Products |
| `/api/products/{product_id}` | GET | Get Product Details |
| `/api/products/create/` | POST | Create Product (Admin) |
| `/api/products/update/{product_id}` | PUT | Update Product (Admin) |
| `/api/products/delete/{product_id}` | DELETE | Delete Product (Admin) |
| `/api/product-variants/{variant_id}` | GET | Get ProductVariant Detail |
| `/api/product-variants/product_variants` | GET | Get ProductVariants Details |
| `/api/product-variants/create/` | POST | Create ProProductVariantduct (Admin) |
| `/api/product-variants/update/{variant_id}` | PUT | Update ProductVariant (Admin) |
| `/api/product-variants/delete/{variant_id}` | DELETE | Delete ProductVariant (Admin) |

---

### 5. 📦 Order Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/orders/create` | POST | Place New Order |
| `/api/orders/{order_id}` | GET | Get Order Details |
| `/api/orders/orders` | GET | List User Orders |
| `/api/orders/update/{order_id}/status` | PUT | Update Order Status (Admin) |

---

### 6. 🛒 Cart & Checkout

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/carts/create` | POST | Add Item to Cart |
| `/api/carts/{item_id}` | GET | Get Cart Items |
| `/api/carts//{item_id}` | DELETE | Remove Item from Cart |
| `/api/carts/checkout` | POST | Checkout and Create Order |

---

### 7. 💳 Payment Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/payments/create` | POST | Initiate Payment |
| `/api/payments/verify/{transaction_id}` | GET | Verify Payment Status |

---

### 8. ⭐ Review & Rating

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reviews/create` | POST | Add Product Review |
| `/api/reviews/{review_id}` | GET | Get Reviews for Product |

---

### 9. 🔔 Notifications

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notifications` | GET | List Order Notifications |
| `/api/notifications/{notification_id}` | PUT | Mark Notification as Read |

---

### 10. 📊 Admin Reporting

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reports/sales` | GET | Get Sales Report |
| `/api/reports/users` | GET | Get User Analytics |
| `/api/reports/dashboard/stats` | GET | Get Summary Stats |

---


## 📖 Getting Started
## Installation <a name="installation"></a>
#### Prerequisites <a name="prerequisites"></a>
Before running the File Ingestion Process, ensure you have the following prerequisites installed:
- Python 3.x
- PostgreSQL database

## Configuration <a name="configuration"></a>
Create database_credentials file and fill in the info
```bash
nano /home/ubuntu/database_credentials/config.ini
[database]
webapphost=localhost
webappport=5432
webappusername=database_username
webapppassword=database_password
webappdatabase_name=database_name
```

### 1. Clone the Repo <a name="Clone the Repo"></a>
```bash
git clone https://github.com/Arshavin023/pizzadelivery_api.git
cd pizzadelivery_api
```

### 2. Create and Activate Virtual Environment <a name="create and activate virtual environment"></a>
```bash
python3 -m venv pizzadelivery_venv && source pizzadelivery_venv/bin/activate
```

### 3. Install Python Packages <a name="Install the required Python packages"></a>
```bash
pip install -r requirements.txt
```

### 4. Run App For Testing <a name="Run App to Test Endpoints"></a>
```bash
uvicorn main:app --reload
```

## Deployment <a name="deployment"></a>

## License <a name="license"></a>
- MIT License

## Authors & Acknowledgements <a name="authors_and_acknowledgments"></a>
- Uche Nnodim
