import React, { useState, useEffect } from "react";
import BarcodeScannerComponent from "react-qr-barcode-scanner";
import "./productModal.css";

export default function ProductModal({ onClose }) {
  const [image, setImage] = useState(null);
  const [barcodeData, setBarcodeData] = useState("");
  const [showScanner, setShowScanner] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState("");
  const [currency, setCurrency] = useState("USD");

  // Pricing fields
  const [wholesalePrice, setWholesalePrice] = useState("");
  const [retailPrice, setRetailPrice] = useState("");
  const [wholesaleSelling, setWholesaleSelling] = useState("");
  const [retailSelling, setRetailSelling] = useState("");

  // Discount prices (up to 3 entries each)
  const [wholesaleDiscounts, setWholesaleDiscounts] = useState([{ price: "", percentage: "", isValid: false }]);
  const [retailDiscounts, setRetailDiscounts] = useState([{ price: "", percentage: "", isValid: false }]);

  // GST
  const [gstIncluded, setGstIncluded] = useState(false);
  const [gstExcluded, setGstExcluded] = useState(false);
  const [wholesaleGST, setWholesaleGST] = useState("");
  const [retailGST, setRetailGST] = useState("");

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

   // Description and Attributes
  const [description, setDescription] = useState("");
  const [attributes, setAttributes] = useState([{ name: "", value: "" }]);
 
  // Ordered list of units
  const unitOptions = [
    "mm", "cm", "m", "in", "ft", "yd",
    "pc", "dozen", "pack", "ctn", "pallet", "Ream",
    "oz", "g", "kg", "lb", "ton",
    "l", "c", "pt", "qt", "gal", "bbl"
  ];


    // Handle barcode scan
    const handleScan = (err, result) => {
      if (result) {
        setBarcodeData(result.text); // Save barcode
        setShowScanner(false); // Hide scanner after scan
      }
    };

  // Price validation (ensures correct decimal formatting)
  const formatPrice = (value) => {
    if (!value) return "";
    if (!/^\d*\.?\d*$/.test(value)) return ""; // Allow only numbers and one decimal
    return value.includes(".") ? parseFloat(value).toFixed(2) : `${value}.00`;
  };

  // Handle discount addition/removal
  const addDiscount = (setter, discounts) => {
    setter((prev) => (prev.length < 3 ? [...prev, { price: "", percentage: "", isValid: false }] : prev));
  };

  const removeDiscount = (setter, index) => {
    setter((prev) => prev.filter((_, i) => i !== index));
  };

  // Handle discount calculation
  const handleDiscountChange = (setter, index, value, type, sellingPrice) => {
    setter((prev) => {
      const newDiscounts = [...prev];
      newDiscounts[index][type] = value;

      // Calculate price if percentage is entered
      if (type === "percentage" && value) {
        const discountAmount = (parseFloat(sellingPrice || 0) * parseFloat(value)) / 100;
        newDiscounts[index].price = (parseFloat(sellingPrice || 0) - discountAmount).toFixed(2);
      }

      // If price is entered manually, keep it as it is
      if (type === "price" && value) {
        newDiscounts[index].price = value;
      }

      // Mark as valid if any field is filled
      newDiscounts[index].isValid = newDiscounts[index].price !== "" || newDiscounts[index].percentage !== "";

      return newDiscounts;
    });
  };

   // Handle description change
   const handleDescriptionChange = (event) => {
    setDescription(event.target.value);
  };

  // Handle dynamic addition of attributes (up to 5)
  const addAttribute = () => {
    // Check if both the Name and Value fields are filled in the last attribute before adding
    const lastAttribute = attributes[attributes.length - 1];
    if (lastAttribute.name !== "" && lastAttribute.value !== "") {
      if (attributes.length < 5) {
        setAttributes([...attributes, { name: "", value: "" }]);
      }
    }
  };

  const removeAttribute = (index) => {
    setAttributes(attributes.filter((_, i) => i !== index));
  };

  const handleAttributeChange = (index, field, value) => {
    const updatedAttributes = [...attributes];
    updatedAttributes[index][field] = value;
    setAttributes(updatedAttributes);
  };

  // GST Calculation
  useEffect(() => {
    if (gstIncluded && wholesaleSelling) {
      setWholesaleGST((parseFloat(wholesaleSelling) * 12) / 112); // GST already in price
    } else if (gstExcluded && wholesaleSelling) {
      setWholesaleGST((parseFloat(wholesaleSelling) * 12) / 100); // Add 12% GST
    } else {
      setWholesaleGST("");
    }

    if (gstIncluded && retailSelling) {
      setRetailGST((parseFloat(retailSelling) * 12) / 112);
    } else if (gstExcluded && retailSelling) {
      setRetailGST((parseFloat(retailSelling) * 12) / 100);
    } else {
      setRetailGST("");
    }
  }, [gstIncluded, gstExcluded, wholesaleSelling, retailSelling]);

  // Handle price formatting on blur
  const handleBlur = (setter, value) => {
    setter(formatPrice(value));
  };

  // Handle discount price blur
  const handleDiscountBlur = (setter, index, value, type, sellingPrice) => {
    const formattedValue = formatPrice(value);
    handleDiscountChange(setter, index, formattedValue, type, sellingPrice);
  };

  // Helper function to check if at least one discount field is filled
  const isDiscountValid = (discounts) => {
    return discounts.some(
      (discount) => discount.price !== "" || discount.percentage !== ""
    );
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>New Product</h2>
        <div className="image-upload">
          <label htmlFor="image-upload" className="image-holder">
            {image ? <img src={image} alt="Product" /> : "Drag image or Browse"}
          </label>
          <input id="image-upload" type="file" accept="image/*" onChange={handleImageUpload} hidden />
        </div>
        <form>
          {/* Barcode */}
          <section>
          <label>
            Barcode:
            <input type="text" name="barcode" value={barcodeData} readOnly />
          </label>

          <div className="barcode-buttons">
            <button type="button" onClick={() => setShowScanner(true)}>Add Barcode</button>           
            <button type="button">Generate Barcode</button>
          </div>

          {showScanner && (
            <BarcodeScannerComponent width={300} height={100} onUpdate={handleScan} />
          )}
        
              <label>
                Product Name
                <input type="text" placeholder="Enter product name" required />
              </label>
            <label>
                Category
                <input type="text" placeholder="Enter category" required />
              </label>
              <label>
                SKU
                <input type="text" placeholder="Enter product SKU" required />
              </label>



                                 
<label>
                Quantity
                <input type="number" placeholder="Enter quantity" required />
              </label>

          <label>
            Unit
            <select value={selectedUnit} onChange={(e) => setSelectedUnit(e.target.value)} required>
              <option value="">Select Unit</option>
              {unitOptions.map((unit) => (
                <option key={unit} value={unit}>{unit}</option>
              ))}
            </select>
          </label>

              <label>
                Expiry Date
                <input type="date" required />
              </label>
              
              <label>
                Threshold Value
                <input type="number" placeholder="Enter threshold value" required />
              </label>
               
           {/* Description */}
           <label>
            Description:
            <textarea 
              value={description} 
              onChange={handleDescriptionChange} 
              placeholder="Enter product description"
            />
          </label>

          {/* Attributes */}
          <label>Attributes</label>
          {attributes.map((attribute, index) => (
            <div key={index} className="attribute-row">
              <input 
                type="text" 
                placeholder="Name" 
                value={attribute.name} 
                onChange={(e) => handleAttributeChange(index, "name", e.target.value)} 
              />
              <input 
                type="text" 
                placeholder="Value" 
                value={attribute.value} 
                onChange={(e) => handleAttributeChange(index, "value", e.target.value)} 
              />
              {index === attributes.length - 1 && attributes.length < 5 && (
                <button type="button" onClick={addAttribute}>Add</button>
              )}
              {attributes.length > 1 && (
                <button type="button" onClick={() => removeAttribute(index)}>Remove</button>
              )}
            </div>
          ))}
          </section>
          <section>
            {/* Prices */}
          <label>
            Wholesale Purchasing Price
            <input 
              type="text" 
              value={wholesalePrice} 
              onChange={(e) => setWholesalePrice(e.target.value)} 
              onBlur={(e) => handleBlur(setWholesalePrice, e.target.value)} 
            />
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="USD">USD</option>
              <option value="LRD">LRD</option>
            </select>
          </label>

          <label>
            Retail Purchasing Price
            <input 
              type="text" 
              value={retailPrice} 
              onChange={(e) => setRetailPrice(e.target.value)} 
              onBlur={(e) => handleBlur(setRetailPrice, e.target.value)} 
            />
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="USD">USD</option>
              <option value="LRD">LRD</option>
            </select>
          </label>

          <label>
            Wholesale Selling Price
            <input 
              type="text" 
              value={wholesaleSelling} 
              onChange={(e) => setWholesaleSelling(e.target.value)} 
              onBlur={(e) => handleBlur(setWholesaleSelling, e.target.value)} 
            />
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="USD">USD</option>
              <option value="LRD">LRD</option>
            </select>
            <div>
              <input 
                type="checkbox" 
                checked={gstIncluded} 
                onChange={() => {
                  setGstIncluded(true);
                  setGstExcluded(false);
                }} 
              /> GST Included
              <input 
                type="checkbox" 
                checked={gstExcluded} 
                onChange={() => {
                  setGstExcluded(true);
                  setGstIncluded(false);
                }} 
              /> GST Excluded
            </div>
            {wholesaleGST && <span>GST: {wholesaleGST.toFixed(2)}</span>}
          </label>

          <label>
            Retail Selling Price
            <input 
              type="text" 
              value={retailSelling} 
              onChange={(e) => setRetailSelling(e.target.value)} 
              onBlur={(e) => handleBlur(setRetailSelling, e.target.value)} 
            />
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="USD">USD</option>
              <option value="LRD">LRD</option>
            </select>
            {retailGST && <span>GST: {retailGST.toFixed(2)}</span>}
          </label>

          {/* Discounted Prices */}
          <label>Wholesale Discount Price</label>
          {wholesaleDiscounts.map((discount, index) => (
            <div key={index} className="discount-row">
              <input 
                type="text" 
                value={discount.price} 
                onChange={(e) => handleDiscountChange(setWholesaleDiscounts, index, e.target.value, "price", wholesaleSelling)} 
                onBlur={(e) => handleDiscountBlur(setWholesaleDiscounts, index, e.target.value, "price", wholesaleSelling)}
              />
              <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="USD">USD</option>
              <option value="LRD">LRD</option>
            </select>
              <input 
                type="number" 
                placeholder="%" 
                value={discount.percentage} 
                onChange={(e) => handleDiscountChange(setWholesaleDiscounts, index, e.target.value, "percentage", wholesaleSelling)} 
              />
              {index === wholesaleDiscounts.length - 1 && wholesaleDiscounts.length < 3 && (
                <button 
                  type="button" 
                  onClick={() => addDiscount(setWholesaleDiscounts)} 
                  disabled={!discount.isValid}
                >
                  +
                </button>
              )}
              {wholesaleDiscounts.length > 1 && (
                <button type="button" onClick={() => removeDiscount(setWholesaleDiscounts, index)}>-</button>
              )}
            </div>
          ))}

          <label>Retail Discount Price</label>
          {retailDiscounts.map((discount, index) => (
            <div key={index} className="discount-row">
              <input 
                type="text" 
                value={discount.price} 
                onChange={(e) => handleDiscountChange(setRetailDiscounts, index, e.target.value, "price", retailSelling)} 
                onBlur={(e) => handleDiscountBlur(setRetailDiscounts, index, e.target.value, "price", retailSelling)}
              /> 
              <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="USD">USD</option>
              <option value="LRD">LRD</option>
            </select>
              <input 
                type="number" 
                placeholder="%" 
                value={discount.percentage} 
                onChange={(e) => handleDiscountChange(setRetailDiscounts, index, e.target.value, "percentage", retailSelling)} 
              />
              {index === retailDiscounts.length - 1 && retailDiscounts.length < 3 && (
                <button 
                  type="button" 
                  onClick={() => addDiscount(setRetailDiscounts)} 
                  disabled={!discount.isValid}
                >
                  +
                </button>
              )}
              {retailDiscounts.length > 1 && (
                <button type="button" onClick={() => removeDiscount(setRetailDiscounts, index)}>-</button>
              )}
            </div>
          ))}
          </section>
          {/* Submit Buttons */}
          
        </form>
        <div className="modal-actions">
            <button type="button" onClick={onClose}>Discard</button>
            <button type="submit">Add Product</button>
          </div>
      </div>
    </div>
  );
}
