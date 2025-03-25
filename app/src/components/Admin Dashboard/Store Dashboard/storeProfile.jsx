import { useState } from "react";
import "./storeProfile.css";

export default function StoreProfile({ store, onClose, onSave }) {
  const [formData, setFormData] = useState(
    store || { name: "", address: "", city: "", country: "", contact: "" }
  );

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>{store ? "Edit Store" : "Add Store"}</h2>
        <form>
          <label>Store/Branch Name</label>
          <input type="text" name="name" value={formData.name} onChange={handleChange} required />

          <label>Address</label>
          <input type="text" name="address" value={formData.address} onChange={handleChange} required />

          <label>City</label>
          <input type="text" name="city" value={formData.city} onChange={handleChange} required />

          <label>Country</label>
          <input type="text" name="country" value={formData.country} onChange={handleChange} required />

          <label>Contact</label>
          <input type="text" name="contact" value={formData.contact} onChange={handleChange} required />

          <div className="button-group">
            <button type="button" className="discard" onClick={onClose}>Discard</button>
            <button type="submit" className="save" onClick={(e) => { e.preventDefault(); onSave(formData); }}>
              {store ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
