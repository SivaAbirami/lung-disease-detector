import axios from "axios";
import toast from "react-hot-toast";

const api = axios.create({
  baseURL: "/api",
  withCredentials: false,
  timeout: 20000
});

api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.error ||
      error.message ||
      "Unexpected error, please try again.";
    toast.error(message);
    return Promise.reject(error);
  }
);

export const uploadImage = (file) => {
  const formData = new FormData();
  formData.append("image", file);
  return api.post("/predict/", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
};

export const getTaskStatus = (taskId, predictionId) =>
  api.get(`/task/${taskId}/`, { params: predictionId ? { prediction_id: predictionId } : {} });

export const getPredictionHistory = (params) =>
  api.get("/predictions/", { params });

export const getRecommendations = (diseaseName) =>
  api.get(`/recommendations/${encodeURIComponent(diseaseName)}/`);

export const submitFeedback = (predictionId, trueClass) =>
  api.post(`/predictions/${predictionId}/feedback/`, { true_class: trueClass });

export default api;
