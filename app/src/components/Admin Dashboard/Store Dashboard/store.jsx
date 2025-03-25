import { useState } from "react";
import "./store.css";
import StoreProfile from "./storeProfile";
function StoreCard({ store, onEdit }) {
  return (
    <div className="store-card">
      <div className="store-name">{store.name}</div>
      <div className="store-details">
        <p>{store.address}</p>
        <p>{store.city}, {store.country}</p>
        <p>{store.contact}</p>
        <p><strong>Manager:</strong> {store.managerName}</p>
        <p><strong>Manager Contact:</strong> {store.managerContact}</p>
        <button className="edit-button" onClick={() => onEdit(store)}>Edit</button>
      </div>
    </div>
  );
}

export default function Stores() {
  const [stores] = useState([
    { name: "Store A", address: "123 Main St", city: "Paynesville City", country: "Liberia", contact: "+231-770-123-456", managerName: "John Doe", managerContact: "987-654-3210" },
    { name: "Store B", address: "456 Elm St", city: "Paynesville City", country: "Liberia", contact: "111-222-3333", managerName: "Jane Smith", managerContact: "444-555-6666" },
    { name: "Store C", address: "789 Oak St", city: "Paynesville City", country: "Liberia", contact: "999-888-7777", managerName: "Alice Johnson", managerContact: "666-777-8888" },
    { name: "Store A", address: "123 Main St", city: "Paynesville City", country: "Liberia", contact: "+231-770-123-456", managerName: "John Doe", managerContact: "987-654-3210" },
    { name: "Store B", address: "456 Elm St", city: "Paynesville City", country: "Liberia", contact: "111-222-3333", managerName: "Jane Smith", managerContact: "444-555-6666" },
    { name: "Store C", address: "789 Oak St", city: "Paynesville City", country: "Liberia", contact: "999-888-7777", managerName: "Alice Johnson", managerContact: "666-777-8888" }
  ]);

  const [selectedStore, setSelectedStore] = useState(null);
  const [showProfile, setShowProfile] = useState(false);

  const handleAddStore = () => {
    setSelectedStore(null);
    setShowProfile(true);
  };

  const handleEditStore = (store) => {
    setSelectedStore(store);
    setShowProfile(true);
  };

  const handleCloseProfile = () => {
    setShowProfile(false);
  };

  const handleSaveStore = (storeData) => {
    if (selectedStore) {
      setStores(stores.map((s) => (s.name === selectedStore.name ? storeData : s)));
    } else {
      setStores([...stores, storeData]);
    }
    setShowProfile(false);
  };

  return (
    <div className="store-container">
      <div className="store-header">
        <h2>Manage Stores</h2>
        <button className="add-store" onClick={handleAddStore}>Add Store</button>
      </div>
      <div className="store-list scrollable">
        {stores.map((store, index) => (
          <StoreCard key={index} store={store} onEdit={handleEditStore} />
        ))}
      </div>
      {showProfile && <StoreProfile store={selectedStore} onClose={handleCloseProfile} onSave={handleSaveStore} />}
    </div>
  );
}
