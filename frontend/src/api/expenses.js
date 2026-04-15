import client from "./client";

export const uploadReceipt = (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  return client.post("/api/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
};

export const getExpenses = (params) =>
  client.get("/api/expenses", { params });

export const deleteExpense = (id) =>
  client.delete(`/api/expenses/${id}`);

export const updateExpense = (id, data) =>
  client.put(`/api/expenses/${id}`, data);

export const getSummary = (month) =>
  client.get("/api/summary", { params: month ? { month } : {} });
