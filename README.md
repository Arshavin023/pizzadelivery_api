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
| `/refresh-token` | POST | Refresh JWT Token |
| `/logout` | POST | User Logout |
| `/roles` | GET | Get Roles (Admin) |
| `/assign-role` | POST | Assign Role to User (Admin) |

---

### 2. 📦 Order Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orders` | POST | Place New Order |
| `/orders/{id}` | GET | Get Order Details |
| `/orders` | GET | List User Orders |
| `/orders/{id}/status` | PUT | Update Order Status (Admin) |

---

### 3. 👤 User Profile & Address

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/profile` | GET | Get User Profile |
| `/profile` | PUT | Update User Profile |
| `/profiles` | GET | Get All Users |

---

### 4. 🛍️ Product Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/products` | GET | List Products |
| `/products/{id}` | GET | Get Product Details |
| `/products` | POST | Create Product (Admin) |
| `/products/{id}` | PUT | Update Product (Admin) |
| `/products/{id}` | DELETE | Delete Product (Admin) |

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

### 1. Clone the Repo
```bash
git clone https://github.com/Arshavin023/pizzadelivery_api.git
cd pizzadelivery_api
