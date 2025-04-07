import React, { useState, useEffect } from "react";
import BarcodeScannerComponent from "react-qr-barcode-scanner";
import "./productModal.css";
import CategoryForm from "./categoryform";
import { useApi } from "../../ApiContext.jsx";
import { useNavigate } from "react-router-dom";

export default function ProductModal({ onClose, onProductAdded }) {
  const navigate = useNavigate();

  const { categories, addProduct } = useApi();
  const [selectedCategory, setSelectedCategory] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false); // State for modal visibility

 
  const [barcodeData, setBarcodeData] = useState("");
  const [showScanner, setShowScanner] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState("");
  const [currency, setCurrency] = useState("USD");
  
  // Discount prices (up to 3 entries each)
  const [wholesaleDiscounts, setWholesaleDiscounts] = useState([{ price: "", percentage: "", isValid: false }]);
  const [retailDiscounts, setRetailDiscounts] = useState([{ price: "", percentage: "", isValid: false }]);

  // state variables for Wholesale GST Included/Excluded
  const [wholesaleGstIncluded, setwholesalewholesaleGstIncluded] = useState(false);
  const [wholesaleGstExcluded, setwholesaleGstExcluded] = useState(false);
  const [wholesaleGST, setWholesaleGST] = useState(""); //Wholesale GST Statee

  //  state variables for Retail GST Included/Excluded
  const [gstRetailIncluded, setGstRetailIncluded] = useState(false);
  const [gstRetailExcluded, setGstRetailExcluded] = useState(false);
  const [retailGST, setRetailGST] = useState(""); // Retail GST State



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
  const addDiscount = (setter) => {
    setter((prev) => (prev.length < 3 ? [...prev, { price: "", percentage: "", isValid: false }] : prev));
  };

  const removeDiscount = (setter, index) => {
    setter((prev) => prev.filter((_, i) => i !== index));
  };

  // Handle discount calculation
  const handleDiscountChange = (setter, index, value, type) => {
    setter((prev) => {
      const newDiscounts = [...prev];
      newDiscounts[index][type] = value;

      const wholesalePrice = parseFloat(formData.lots[0].wholesale_selling_price); // Get wholesale selling price
      // Calculate price if percentage is entered
      if (type === "percentage" && value) {
        const discountAmount = (wholesalePrice * parseFloat(value)) / 100;
        newDiscounts[index].price = (wholesalePrice - discountAmount).toFixed(2);
      }
      const retailPrice = parseFloat(formData.lots[0].retail_selling_price); // Get wholesale selling price
      // Calculate price if percentage is entered
      if (type === "percentage" && value) {
        const discountAmount = (retailPrice * parseFloat(value)) / 100;
        newDiscounts[index].price = (retailPrice - discountAmount).toFixed(2);
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

  const handleAttributeChange = (index, e) => {
    const { name, value } = e.target;
    const updatedAttributes = [...attributes];
    updatedAttributes[index][name] = value;
    setAttributes(updatedAttributes);
  };

  // Handle price formatting on blur
  const handleBlur = (setter, value) => {
    setter(formatPrice(value));
  };

  // Handle discount price blur
  const handleDiscountBlur = (setter, index, value, type, sellingPrice) => {
    const formattedValue = formatPrice(value);
    handleDiscountChange(setter, index, formattedValue, type, sellingPrice);
  };

  const [formData, setFormData] = useState({
    product_name: '',
    category: '',
    unit: '',
    description: '',
    threshold_value: '',
    product_image: null,
    attributes: [],
    lots: [
      {
        purchased_date: "",
        quantity: "",
        expired_date: "",
        wholesale_purchase_price: "",
        retail_purchase_price: "",
        wholesale_selling_price: "",
        retail_selling_price: "",
        wholesale_discount_price: [],
        retail_discount_price: []
      }
    ]
  });
  

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleLotChange = (index, e) => {
    const { name, value } = e.target;
    
    setFormData((prevFormData) => {
      const newLots = [...prevFormData.lots];
      newLots[index][name] = value; // This updates wholesale_selling_price in the formData
      return { ...prevFormData, lots: newLots };
    });
  };

  // GST Calculation
  useEffect(() => {
    // GST Calculation for Wholesale Price
    if (wholesaleGstIncluded && formData.lots[0].wholesale_selling_price) {
      // GST is included in price, calculate GST amount
      setWholesaleGST((parseFloat(formData.lots[0].wholesale_selling_price) * 12) / 100); // GST portion when price includes GST
    } else if (wholesaleGstExcluded && formData.lots[0].wholesale_selling_price) {
      // Add 12% GST to the price if GST is excluded
      setWholesaleGST((parseFloat(formData.lots[0].wholesale_selling_price) * 12) / 100); // GST amount when price excludes GST
    } else {
      setWholesaleGST(""); // Clear GST if no price is available
    }
  
    // GST Calculation for Retail Price
    if (gstRetailIncluded && formData.lots[0].retail_selling_price) {
      // GST is included in price, calculate GST amount
      setRetailGST((parseFloat(formData.lots[0].retail_selling_price) * 12) / 100); // GST portion when price includes GST
    } else if (gstRetailExcluded && formData.lots[0].retail_selling_price) {
      // Add 12% GST to the price if GST is excluded
      setRetailGST((parseFloat(formData.lots[0].retail_selling_price) * 12) / 100); // GST amount when price excludes GST
    } else {
      setRetailGST(""); // Clear GST if no price is available
    }
  }, [wholesaleGstIncluded, wholesaleGstExcluded, gstRetailIncluded, gstRetailExcluded, formData.lots[0].wholesale_selling_price, formData.lots[0].retail_selling_price]);
  
  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const newProduct = await addProduct(
        formData,
        selectedCategory,
        selectedUnit,
        attributes,
        wholesaleDiscounts,
        retailDiscounts
      );

      if (newProduct && onProductAdded) {
        onProductAdded(newProduct);
      }
    } catch (err) {
      console.error("Failed to handle product submit:", err);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>New Product</h2>
        
        <button className="open-modal-btn" onClick={() => setIsModalOpen(true)}>
        Create Category
        </button>

        {/* Category Modal */}
        {isModalOpen && <CategoryForm  closeModal={() => setIsModalOpen(false)} />}

        <label>Category:</label>
      

        <form onSubmit={handleSubmit}>
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
        
            <div>
              <label>
                  Product Name:
                  <input type="text" name="product_name" value={formData.product_name} onChange={handleChange} required />
              </label>
              
              <label>
                  Category:
                  <select name="category" value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} required>
                    <option value="">Select a category</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>

              </label>

              <label>
                Unit
                <select name="unit" value={selectedUnit} onChange={(e) => setSelectedUnit(e.target.value)}>
                  <option value="">Select Unit</option>
                  {unitOptions.map((unit) => (
                    <option key={unit} value={unit}>{unit}</option>
                  ))}
                </select>
              </label>

              <label>
                  Description:
                  <textarea name="description" value={formData.description} onChange={handleChange} required />
              </label>

              <label>
                  Threshold Value:
                  <input type="number" name="threshold_value" value={formData.threshold_value} onChange={handleChange} required />
              </label>
            </div>
            
                                 
             
              

          {/* Attributes */}
          <label>Specifications</label>
          {attributes.map((attribute, index) => (
            <div key={index} className="attribute-row">
              <input 
                type="text" 
                name="name" 
                value={attribute.name}  
                onChange={(e) => handleAttributeChange(index, e)} 
                placeholder="Attribute Name"
                required 
              />
              <input 
                          type="text" 
                          name="value" 
                          value={attribute.value} 
                          onChange={(e) => handleAttributeChange(index, e)} 
                          placeholder="Attribute Value" 
                          required 
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

          <section className="lot">
          <label>
              Purchased Date
              <input 
                type="date" 
                name="purchased_date"
                value={formData.lots[0].purchased_date}
                onChange={(e) => handleLotChange(0, e)}
                required 
              />
            </label>
            <label>
              Quantity
              <input 
                type="number" 
                name="quantity"
                value={formData.lots[0].quantity}
                onChange={(e) => handleLotChange(0, e)}
                required 
              />
            </label>

            <label>
              Expiry Date
              <input 
                type="date" 
                name="expired_date"
                value={formData.lots[0].expired_date}
                onChange={(e) => handleLotChange(0, e)}
                required 
              />
            </label>
            {/* Prices */}
          <label>
            Wholesale Purchasing Price
            <input 
              type="text" 
              name="wholesale_purchase_price"
              value={formData.lots[0].wholesale_purchase_price}
              onChange={(e) => handleLotChange(0, e)}
              onBlur={(e) => handleBlur((value) => handleLotChange(0, { target: { name: 'wholesale_purchase_price', value } }), e.target.value)}
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
              name="retail_purchase_price"
              value={formData.lots[0].retail_purchase_price}
              onChange={(e) => handleLotChange(0, e)}
              onBlur={(e) => handleBlur((value) => handleLotChange(0, { target: { name: 'retail_purchase_price', value } }), e.target.value)}
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
              name="wholesale_selling_price"
              value={formData.lots[0].wholesale_selling_price}
              onChange={(e) => handleLotChange(0, e)}
              onBlur={(e) => handleBlur((value) => handleLotChange(0, { target: { name: 'wholesale_selling_price', value } }), e.target.value)}
            />
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="USD">USD</option>
              <option value="LRD">LRD</option>
            </select>
            <div>
              <input 
                type="checkbox" 
                checked={wholesaleGstIncluded} 
                onChange={() => {
                  setwholesalewholesaleGstIncluded(true);
                  setwholesaleGstExcluded(false);
                }} 
              /> GST Included
              <input 
                type="checkbox" 
                checked={wholesaleGstExcluded} 
                onChange={() => {
                  setwholesaleGstExcluded(true);
                  setwholesalewholesaleGstIncluded(false);
                }} 
              /> GST Excluded
            </div>
            {wholesaleGST && <span>GST: {wholesaleGST.toFixed(2)}</span>}
          </label>

         
          <label>
  Retail Selling Price
  <input 
    type="text" 
    name="retail_selling_price" 
    value={formData.lots[0].retail_selling_price}
    onChange={(e) => handleLotChange(0, e)}
    onBlur={(e) => handleBlur((value) => handleLotChange(0, { target: { name: 'retail_selling_price', value } }), e.target.value)}
  />
  <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
    <option value="USD">USD</option>
    <option value="LRD">LRD</option>
  </select>
  <div>
    {/* Retail GST Included Checkbox */}
    <input 
      type="checkbox" 
      checked={gstRetailIncluded} 
      onChange={() => {
        setGstRetailIncluded(true);
        setGstRetailExcluded(false);
      }} 
    /> GST Included

    {/* Retail GST Excluded Checkbox */}
    <input 
      type="checkbox" 
      checked={gstRetailExcluded} 
      onChange={() => {
        setGstRetailExcluded(true);
        setGstRetailIncluded(false);
      }} 
    /> GST Excluded
  </div>

  {/* Display Retail GST calculation */}
  {retailGST && <span>Retail GST: {retailGST.toFixed(2)}</span>}
</label>
          {/* Discounted Prices */}


<label>
  Wholesale Discount Price
  {wholesaleDiscounts.map((discount, index) => (
    <div key={index} className="discount-row">
      <input 
        type="text" 
        value={discount.price} 
        onChange={(e) => handleDiscountChange(setWholesaleDiscounts, index, e.target.value, "price", formData.lots[0].wholesale_selling_price)} 
        onBlur={(e) => handleDiscountBlur(setWholesaleDiscounts, index, e.target.value, "price", formData.lots[0].wholesale_selling_price)}
        
      />
      <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
        <option value="USD">USD</option>
        <option value="LRD">LRD</option>
      </select>
      <input 
        type="number" 
        placeholder="%" 
        value={discount.percentage} 
        onChange={(e) => handleDiscountChange(setWholesaleDiscounts, index, e.target.value, "percentage", formData.lots[0].wholesale_selling_price)} 
        
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
</label>

<label>
  Retail Discount Price
  {retailDiscounts.map((discount, index) => (
    <div key={index} className="discount-row">
      <input 
        type="text" 
        value={discount.price} 
        onChange={(e) => handleDiscountChange(setRetailDiscounts, index, e.target.value, "price", formData.lots[0].retail_selling_price)} 
        onBlur={(e) => handleDiscountBlur(setRetailDiscounts, index, e.target.value, "price", formData.lots[0].retail_selling_price)}
      />
      <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
        <option value="USD">USD</option>
        <option value="LRD">LRD</option>
      </select>
      <input 
        type="number" 
        placeholder="%" 
        value={discount.percentage} 
        onChange={(e) => handleDiscountChange(setRetailDiscounts, index, e.target.value, "percentage", formData.lots[0].retail_selling_price)} 
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
</label>
          </section>
          
          {/* Submit Buttons */}
          
        </form>
        <div className="modal-actions">
            <button type="button" onClick={onClose}>Discard</button>
            <button type="submit" onClick={handleSubmit}>Add Product</button>
          </div>
      </div>
    </div>
  );
}
