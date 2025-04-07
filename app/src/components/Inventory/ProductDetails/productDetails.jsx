import React, { useState } from "react";
import "./productDetail.css"; // Ensure you have a CSS file for styling



export default function ProductDetail({ product, onClose }) {
  const back_btn = "/arrow.png";


  const [activeTab, setActiveTab] = useState("Overview"); // State to track active tab

  const [image, setImage] = useState(null);
  const handleImageUpload = (event) => {
    const file = event.target.files[0]; // Get uploaded file
    if (file) {
      // setFormData((prevData) => ({ ...prevData, product_image: file }));
  
      const reader = new FileReader();
      reader.onloadend = () => {
        setImage(reader.result); // Update the image preview
      };
      reader.readAsDataURL(file);
    }
  };

  const stockData = [
    { storeName: "Main Branch", stock: 120 },
    { storeName: "Downtown", stock: 85 },
    { storeName: "Uptown", stock: 42 },
    { storeName: "Suburb", stock: 230 },
    { storeName: "Warehouse", stock: 500 },
    { storeName: "Warehouse", stock: 500 },
    { storeName: "Warehouse", stock: 500 },
    // add more to test scroll
  ];
  const renderTabContent = () => {
    switch (activeTab) {
      case "Overview":
        return (
          <section className="tab-content">
            
            <section className="tab-content-product-detail">
              <div className="tab-content-left">
                <h3>Product Details</h3>

                <div className="product-detail">
                  <p className="info">Product Name: </p>
                  <p>{product.product_name}</p>
                </div>

                <div className="product-detail">
                  <p className="info">Product ID: </p>
                  <p>{product.id}</p>
                </div>

                <div className="product-detail">
                  <p className="info">Product Category: </p>
                  <p>{product.category}</p>
                </div>

                <div className="product-detail">
                  <p className="info">Expiry Date: </p>
                  {
                    product.expired_date || 
                    (product.lots && product.lots.length > 0 && product.lots[0].expired_date) || 
                    'N/A'
                  }
                </div>

                <div className="product-detail">
                  <p className="info">Threshold Value: </p>
                  <p>{product.threshold_value}</p>
                </div>

                <section className="supplier-details">
                  <h3>Supplier Details</h3>
                  <div className="product-detail">
                    <p className="info">Supplier Name: </p>
                    <p>{product.name}</p>
                  </div>
                  <div className="product-detail">
                    <p className="info">Contact Number: </p>
                    <p >{product.name} 0770-957-345</p>
                  </div>
                </section>
              </div>

              <div className="tab-content-right"> 
                <section className="image-upload">
                  <label htmlFor="image-upload" className="image-holder">
                    {image ? <img src={image} alt="Product" /> : "Drag image or Browse"}
                  </label>
                  <input id="image-upload" type="file" accept="image/*" onChange={handleImageUpload} hidden />
                </section>

                <section>
                  <div className="product-detail">
                    <p className="info-right">Opening Stock: </p>
                    <p>40</p>
                  </div>

                  <div className="product-detail">
                    <p className="info-right">Remaining Stock: </p>
                    <p>36</p>
                  </div>

                  <div className="product-detail">
                    <p className="info-right">On the way: </p>
                    <p>15</p>
                  </div>
                </section>
              </div>
            </section>

            <section className="tab-content-store-list">
              <h3 className="sticky-heading">Stock Locations</h3>

              <div className="table-wrapper">
                <table className="stock-table">
                  <thead>
                    <tr>
                      <th className="stores">Store Name</th>
                      <th className="stock-detail">Stock at hand</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stockData.map((row, idx) => (
                      <tr key={idx}>
                        <td className="store">{row.storeName}</td>
                        <td className="stock-value">{row.stock}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

          </section>
        );
      case "Purchases":
        return (
          <div className="tab-content">
            <h3>Purchases</h3>
            <p>No purchase data available.</p> {/* Replace with actual data */}
          </div>
        );
      case "Sales":
        return (
          <div className="tab-content">
            <h3>Sales</h3>
            <p>No sales data available.</p> {/* Replace with actual data */}
          </div>
        );
      case "Restock":
        return (
          <div className="tab-content">
            <h3>Restock Information</h3>
            <p>Restock is due in 30 days.</p> {/* Replace with actual restock info */}
          </div>
        );
      default:
        return <div className="tab-content">Select a tab to view information.</div>;
    }
  };

  return (
    <div className="product-detail-container">
      <div className="product-detail-modal">
        {/* Close Button */}
        <section className="model-ctrl">
          <button className="closebtn" onClick={onClose}><img src={back_btn} alt="Back"/></button>
        </section>

        {/* Top Navigation Bar */}
        <div className="product-nav">
          <ul>
            <li
              className={activeTab === "Overview" ? "active" : ""}
              onClick={() => setActiveTab("Overview")}
            >
              Overview
            </li>
            <li
              className={activeTab === "Purchases" ? "active" : ""}
              onClick={() => setActiveTab("Purchases")}
            >
              Purchases
            </li>
            <li
              className={activeTab === "Sales" ? "active" : ""}
              onClick={() => setActiveTab("Sales")}
            >
              Sales
            </li>
            <li
              className={activeTab === "Restock" ? "active" : ""}
              onClick={() => setActiveTab("Restock")}
            >
              Restock
            </li>
          </ul>
        </div>

       <section className="contents">
         {/* Tab Content */}
         {renderTabContent()}
       </section>
      </div>
    </div>
  );
}
