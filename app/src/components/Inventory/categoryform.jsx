import { useState, useEffect } from "react";
import './category.css';
import { useApi } from "../../ApiContext.jsx";

export default function CategoryForm({ closeModal }) {
  const { addCategory } = useApi();
  const [formFields, setFormFields] = useState([{ name: "", description: "" }]);

  const handleAddField = () => {
    if (formFields[formFields.length - 1].name.trim() !== "") {
      setFormFields([...formFields, { name: "", description: "" }]);
    }
  };

  const handleRemoveField = (index) => {
    if (formFields.length > 1) {
      setFormFields(formFields.filter((_, i) => i !== index));
    }
  };

  const handleChange = (index, field, value) => {
    const newFields = [...formFields];
    newFields[index][field] = value;
    setFormFields(newFields);
  };

  const handleSubmit = async () => {
    const validFields = formFields.filter((f) => f.name.trim() !== "");
    if (validFields.length === 0) return;

    for (let category of validFields) {
      await addCategory(category);
    }

    setFormFields([{ name: "", description: "" }]); // Reset form
    closeModal();
  };

  return (
    <div className="category-modal-overlay">
      <div className="category-modal-content">
        <h2>Create Categories</h2>

        {formFields.map((field, index) => (
          <div key={index} className="input-group">
            <input
              type="text"
              placeholder="Name"
              value={field.name}
              onChange={(e) => handleChange(index, "name", e.target.value)}
            />
            <textarea
              placeholder="Description"
              value={field.description}
              onChange={(e) => handleChange(index, "description", e.target.value)}
            />
            {formFields.length > 1 && (
              <button className="remove-btn" onClick={() => handleRemoveField(index)}>
                ❌ Remove
              </button>
            )}
          </div>
        ))}

        <button className="add-btn" onClick={handleAddField} disabled={formFields[formFields.length - 1].name.trim() === ""}>
          + Add Category
        </button>

        <button className="submit-btn" onClick={handleSubmit}>
          Submit
        </button>

        <button className="close-btn" onClick={closeModal}>
          Close
        </button>
      </div>
    </div>
  );
}
