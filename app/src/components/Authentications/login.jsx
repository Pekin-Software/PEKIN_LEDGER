// login.js - Mock login function
export function authenticateUser(email, password) {
    // Mock user data
    const mockUsers = [
      { email: "user@example.com", password: "password123", role: "admin" },
      { email: "manager@example.com", password: "manager123", role: "manager" },
      { email: "cashier@example.com", password: "cashier123", role: "cashier" }
    ];
  
    // Check if user exists and credentials match
    const user = mockUsers.find(
      (user) => user.email === email && user.password === password
    );
  
    if (user) {
      return {
        success: true,
        user: {
          email: user.email,
          role: user.role
        }
      };
    } else {
      return { success: false, message: "Invalid email or password" };
    }
  }
  