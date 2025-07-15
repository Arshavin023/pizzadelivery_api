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
| `/profile` | GET | Get User Profile |
| `/profiles` | GET | Get All User Profiles|
| `/update/user` | PUT | Update User Information |
| `/update/address` | PUT | Update User Address  |

---

### 3. 🛍️ Product Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/products` | GET | List Products |
| `/products/{id}` | GET | Get Product Details |
| `/products` | POST | Create Product (Admin) |
| `/products/{id}` | PUT | Update Product (Admin) |
| `/products/{id}` | DELETE | Delete Product (Admin) |
| `/categories` |  POST  |  Create Category (Admin)  |

---

### 4. 📦 Order Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orders` | POST | Place New Order |
| `/orders/{id}` | GET | Get Order Details |
| `/orders` | GET | List User Orders |
| `/orders/{id}/status` | PUT | Update Order Status (Admin) |

---

### 5. 🗂️ Category & Inventory

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/categories` | POST | Create Category (Admin) |
| `/categories` | GET | List Categories |
| `/categories/{id}` | PUT | Update Category (Admin) |
| `/categories/{id}` | DELETE | Delete Category (Admin) |
| `/inventory/{product_id}` | PUT | Update Inventory (Admin) |

---

### 6. 🛒 Cart & Checkout

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cart` | POST | Add Item to Cart |
| `/cart` | GET | Get Cart Items |
| `/cart/{item_id}` | DELETE | Remove Item from Cart |
| `/checkout` | POST | Checkout and Create Order |

---

### 7. 💳 Payment Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/payment` | POST | Initiate Payment |
| `/payment/verify/{transaction_id}` | GET | Verify Payment Status |

---

### 8. ⭐ Review & Rating

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reviews` | POST | Add Product Review |
| `/products/{id}/reviews` | GET | Get Reviews for Product |

---

### 9. 🔔 Notifications

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notifications` | GET | List Order Notifications |
| `/notifications/{id}` | PUT | Mark Notification as Read |

---

### 10. 📊 Admin Reporting

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reports/sales` | GET | Get Sales Report |
| `/reports/users` | GET | Get User Analytics |
| `/dashboard/stats` | GET | Get Summary Stats |

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
