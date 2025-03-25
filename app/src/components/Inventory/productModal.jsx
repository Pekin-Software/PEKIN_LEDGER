import React, { useState, useEffect } from "react";
import "./productModal.css";

export default function ProductModal({ onClose }) {
  const [image, setImage] = useState(null);

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImage(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };
  useEffect(() => {
    const handleEscapeKey = (event) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleEscapeKey);
    return () => {
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [onClose]);

  const preventClose = (event) => {
    event.stopPropagation();
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" onClick={preventClose}>
        <h2>New Product</h2>
        <div className="image-upload">
          <label htmlFor="image-upload" className="image-holder">
            {image ? <img src={image} alt="Product" /> : "Drag image or Browse"}
          </label>
          <input id="image-upload" type="file" accept="image/*" onChange={handleImageUpload} hidden />
        </div>
        <form>
            <div>
                <label>Product Name</label>
                <input type="text" placeholder="Enter product name" required />
            </div>
            <div>
                <label>Product ID</label>
                <input type="text" placeholder="Enter product ID" required />
            </div>
            <div>
                <label>Category</label>
                <input type="text" placeholder="Enter category" required />        
            </div>
            <div>
                <label>Price</label>
                <input type="number" placeholder="Enter price" required />
            </div>
            <div>
                <label>Quantity</label>
                <input type="number" placeholder="Enter quantity" required />
            </div>
            <div>
                <label>Unit</label>
                <input type="text" placeholder="Enter unit" required />
            </div>
            <div>
                <label>Expiry Date</label>
                <input type="date" required />
            </div>
            <div>
                <label>Threshold Value</label>
                <input type="number" placeholder="Enter threshold value" required />
            </div>          
    
           <div className="modal-actions">
            <button type="button" className="discard" onClick={onClose}>Discard</button>
            <button type="submit" className="add-product">Add Product</button>
          </div>
        </form>
      </div>
    </div>
  );
}
