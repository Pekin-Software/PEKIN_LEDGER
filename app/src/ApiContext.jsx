import { createContext, useContext, useEffect, useState } from "react";
import Cookies from "js-cookie"; // Ensure this package is installed

// Create Context
const ApiContext = createContext();

// Provider Component
export const ApiProvider = ({ children }) => {
  const [categories, setCategories] = useState([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState(null);
  const [products, setProducts] = useState([]);

  // Get Tenant from Cookies
  const tenantDomain = Cookies.get("tenant"); 
  const accessToken = Cookies.get("access_token");
  const csrfToken = Cookies.get("csrftoken");

  const apiBase = `http://${tenantDomain}.localhost:8000/api`;
  const categoriesUrl = `${apiBase}/categories/`;
  const productsUrl = `${apiBase}/products/`;

  // Fetch Categories from API
  const fetchCategories = async () => {
    try {
      const response = await fetch(categoriesUrl, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "Authorization": `Bearer ${accessToken}`, // Manually add the access token
        },
      });

      if (!response.ok) throw new Error("Failed to fetch categories");
      const data = await response.json();
      setCategories(data);
     
    } catch (error) {
      console.error("Error fetching categories:", error);
    }
  };

  // Add New Category to API
  const addCategory = async (newCategory) => {
    try {
      const response = await fetch(categoriesUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "Authorization": `Bearer ${accessToken}`, // Manually add the access token
        },
        body: JSON.stringify(newCategory),
        // credentials: "include", // Sends cookies automatically
      });

      if (!response.ok) {
        // Log the response text or JSON body from the failed request
        const errorResponse = await response.json();
        console.error("Failed to add category, server response:", errorResponse);
        throw new Error(`Failed to add category: ${errorResponse?.detail || response.statusText}`);
      }
  
      const createdCategory = await response.json();
      setCategories((prev) => [...prev, createdCategory]); // Update state
      return createdCategory;
    } catch (error) {
      console.error("Error adding category:", error);
      return null;
    }
  };

  // Add Product to API without image
  const addProduct = async (formData, selectedCategory, selectedUnit, attributes, wholesaleDiscounts, retailDiscounts) => {
    const mappedData = {
      product_name: formData.product_name, // Required
      description: formData.description, // Required
      category: parseInt(selectedCategory, 10), // Convert category to integer
      unit: selectedUnit, // Required
      threshold_value: parseInt(formData.threshold_value, 10), // Convert to integer
      attributes: attributes.map(attr => ({
        name: attr.name,
        value: attr.value,
      })), // Ensure attributes is an array
      lots: formData.lots.map(lot => ({
        purchased_date: lot.purchased_date,
        quantity: parseInt(lot.quantity, 10),
        expired_date: lot.expired_date,
        wholesale_purchase_price: parseFloat(lot.wholesale_purchase_price),
        retail_purchase_price: parseFloat(lot.retail_purchase_price),
        wholesale_selling_price: parseFloat(lot.wholesale_selling_price),
        retail_selling_price: parseFloat(lot.retail_selling_price),
        wholesale_discount_price: wholesaleDiscounts
          .filter(discount => discount.price)
          .map(discount => ({ value: parseFloat(discount.price) })),
        retail_discount_price: retailDiscounts
          .filter(discount => discount.price)
          .map(discount => ({ value: parseFloat(discount.price) })),
      })), // Ensure lots is an array
    };
  
    console.log("Submitting Data:", JSON.stringify(mappedData, null, 2));
  
    try {
      const response = await fetch(productsUrl, {
        method: "POST",
        body: JSON.stringify(mappedData), // Send JSON, not FormData
        headers: { 
          "Content-Type": "application/json", // Required for JSON API
          "X-CSRFToken": csrfToken,
          "Authorization": `Bearer ${accessToken}`,
        },
      });
  
      if (!response.ok) {
        const errorResponse = await response.json();
        console.error("Failed to add product, server response:", errorResponse);
        throw new Error(`Failed to add product: ${errorResponse?.detail || response.statusText}`);
      }
  
      console.log("✅ Product successfully added!");
      const created = await response.json();

    // ✅ Now fetch full product by ID
    const fullResponse = await fetch(`${productsUrl}${created.id}/`, {
      headers: {
        "Authorization": `Bearer ${accessToken}`,
      },
    });

    if (!fullResponse.ok) {
      throw new Error("Failed to fetch full product details");
    }

    const fullProduct = await fullResponse.json();
    return fullProduct;

    } catch (error) {
      console.error("❌ Error adding product:", error);
    }
  };

  //Trying to upload image

  //Fetching product from the API
  const fetchProducts = async () => {
    const productsListUrl = `${productsUrl}list/`;

    setProductsLoading(true);
    setProductsError(null); // Reset error before request
  
    try {
      const response = await fetch(productsListUrl, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "Authorization": `Bearer ${accessToken}`,
        },
      });
  
      if (!response.ok) {
        const errorResponse = await response.json();
        throw new Error(errorResponse?.detail || response.statusText);
      }
      const data = await response.json();
      setProducts(
        data.map(product => ({
          id: product.id,
          product_name: product.product_name,
          category: product.category,
          image: product.image_url || "", // fallback if no image
          available: product.available_status || "In-Stock", // adjust based on backend
          quantity: product.lots?.reduce((sum, lot) => sum + lot.quantity, 0) || 0,
          price: product.lots?.[0]?.retail_selling_price || 0, // or calculate average
          expired_date: product.lots?.[0]?.expired_date || null,
          threshold_value: product.threshold_value,
        }))
      );
      return data;
    } catch (error) {
      console.error("❌ Error fetching products:", error);
      setProducts([]);
      
      setProductsError(error.message || "Unknown error occurred.");
      return [];
    } finally {
      setProductsLoading(false);
    }
    
  };
  
  // Load Categories when Component Mounts
  useEffect(() => {
    if (tenantDomain) fetchCategories();
  }, [tenantDomain]); // Fetch only when tenant is available
  
  return (
    <ApiContext.Provider 
      value={{ 
        categories, 
        addCategory, 
        addProduct,
        fetchProducts,
        products,
        productsLoading,
        productsError,
      }}
    >
      {children}
    </ApiContext.Provider>
  );
};

// Custom Hook to Use API Context
// export const useApi = () => useContext(ApiContext);

function useApi() {
  return useContext(ApiContext);
}

export { useApi };

