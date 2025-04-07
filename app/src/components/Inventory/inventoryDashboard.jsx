import { useState, useRef, useEffect } from "react";
import "./inventoryDashboard.css";
import { Filter } from "lucide-react";
import ProductModal from "./productModal";
import ProductDetail from "./ProductDetails/productDetails";
import { useApi } from "../../ApiContext.jsx";
// const DEFAULT_IMAGE = "";

function Card({ title, value, detail, color }) {
    return (
      <div className="inventory-card">
        <h3 style={{ color }}>{title}</h3>
        <p className="value">{value}</p>
        <p className="detail">{detail}</p>
      </div>
    );
  }
  

function ProductCard({ product, onProductClick}) {
    return (
      <div className="product-card" onClick={() => onProductClick(product)}>
        <div className="product-image-container">
          <img src={product.image || ""} alt={product.name} className="product-image" />
        </div>
        <span className={`availability ${product.available.toLowerCase()}`}>{product.available}</span>
        <h3>{product.name}</h3>
        <p>Quantity: {product.quantity}</p>
        <p>${product.price}</p>
        <button className="update-product">Update</button>
      </div>
    );
  }
  
export default function InventoryDashboard() {
  const { fetchProducts, products, productsLoading, productsError } = useApi();

  useEffect(() => {
    fetchProducts();
  }, []);
 
  const [selectedProduct, setSelectedProduct] = useState(null);

  const [showFilter, setShowFilter] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const filterRef = useRef(null);

  useEffect(() => {
      function handleClickOutside(event) {
        if (filterRef.current && !filterRef.current.contains(event.target)) {
          setShowFilter(false);
        }
      }
      document.addEventListener("mousedown", handleClickOutside);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
      };
  }, []);

  const handleFilterClick = (option) => {
      setShowFilter(false);  
  };

   // Handle when a product card is clicked
  const handleProductClick = (product) => {
    setSelectedProduct(product); // Set the selected product
  };

  return (
    <div className="inventory-container">
         {productsLoading ? (
        <p>Loading products...</p>
      ) : productsError ? (
        <p>Error: {productsError}</p>
      ) : !selectedProduct ? (
          <>
            <section className="overview">
              <h2>Inventory Overview</h2>
              <div className="card-container">
                <Card title="Total Products" value={500} detail="All stocked items" color="blue" />
                <Card title="Categories" value={20} detail="Product Group" color="red" />
                <Card title="Top Selling" value={500} detail="Highest sales volume" color="blue" />
                <Card title="In Stock" value={5} detail="Reorder soon" color="green" />
                <Card title="Out of Stock" value={5} detail="Reorder soon" color="orange" />
                <Card title="Low Stock" value={20} detail="Needs restocking" color="red" />
                <Card title="Expiring Soon" value={15} detail="Check expiry dates" color="purple" />
                <Card title="Total Value" value={150000} detail="Inventory worth" color="green" />
              </div>
            </section>

            <section className="products">
              <div className="products-header">
                <h2>Products</h2>
                <div className="actions">

                  <button className="add-product" onClick={() => setShowModal(true)}>Add Product</button>

                  <div className="filter-container" ref={filterRef}>
                    <button className="filter-button" onClick={() => setShowFilter(!showFilter)}>
                      <span className="filter-icon"><Filter size={16} /></span>
                      <span className="filter-text">Filter</span>
                    </button>
                    {showFilter && (
                      <ul className="filter-options">
                        <li onClick={() => handleFilterClick("In-Stock")}>In-Stock</li>
                        <li onClick={() => handleFilterClick("Out-of-Stock")}>Out-of-Stock</li>
                        <li onClick={() => handleFilterClick("Low Stock")}>Low Stock</li>
                        <li onClick={() => handleFilterClick("Prices: Low to High")}>Prices: Low to High</li>
                        <li onClick={() => handleFilterClick("Prices: High to Low")}>Prices: High to Low</li>
                        <li onClick={() => handleFilterClick("Expiring Date")}>Expiring Date</li>
                      </ul>
                    )}
                  </div>
                  <button className="download">Download All</button>
                </div>
              </div>
              
              <div className="product-grid scrollable">
                {products.map((product) => (
                  <ProductCard key={product.id} product={product} onProductClick={handleProductClick}/>
                ))}
              </div>
      

            </section>
          </>
        ):(
           // Show only ProductDetail if a product is selected
          <ProductDetail product={selectedProduct} onClose={() => setSelectedProduct(null)} />
        )
      }
         {/* Show ProductModal when modal is open */}
        {showModal && (
          <ProductModal 
            onClose={() => setShowModal(false)} 
            onProductAdded={(newProduct) => {
              setSelectedProduct(newProduct); // 👈 open product details view
              setShowModal(false); // 👈 close modal
            }} 
          />
        )}

      </div>

    );
}
  