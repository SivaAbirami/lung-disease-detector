import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import toast from "react-hot-toast";
import { FiUploadCloud } from "react-icons/fi";
import LoadingSpinner from "@components/common/LoadingSpinner";
import { usePrediction } from "@hooks/usePrediction";
import {
  ACCEPTED_TYPES,
  MAX_FILE_SIZE_BYTES,
  isImageFile,
  isWithinSizeLimit,
  getImageDimensions,
  formatFileSize
} from "@utils/validators";

const MIN_DIM = 224;

const Upload = () => {
  const { file, setFile, isSubmitting, isPolling, submit } = usePrediction();
  const [preview, setPreview] = useState(null);
  const [dimError, setDimError] = useState("");

  const onDrop = useCallback(
    async (acceptedFiles) => {
      const picked = acceptedFiles[0];
      if (!picked) return;

      if (!isImageFile(picked)) {
        toast.error("Only JPG and PNG images are allowed.");
        return;
      }
      if (!isWithinSizeLimit(picked)) {
        toast.error("File too large. Maximum allowed size is 10MB.");
        return;
      }

      try {
        const { width, height } = await getImageDimensions(picked);
        if (width < MIN_DIM || height < MIN_DIM) {
          setDimError(`Image is too small (${width}x${height}). Minimum is ${MIN_DIM}x${MIN_DIM}px.`);
          toast.error("Image dimensions are too small for reliable analysis.");
          return;
        }
        setDimError("");
      } catch {
        toast.error("Could not read image dimensions.");
        return;
      }

      setFile(picked);
      setPreview(URL.createObjectURL(picked));
    },
    [setFile]
  );

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    fileRejections
  } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"]
    },
    maxSize: MAX_FILE_SIZE_BYTES,
    multiple: false
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    await submit();
  };

  return (
    <section aria-label="Upload chest X-ray for AI analysis" className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-50">
          Upload Chest X-ray
        </h1>
        <p className="mt-1 text-sm text-slate-400 max-w-2xl">
          Securely upload a chest X-ray image to screen for COVID-19, Tuberculosis,
          Pneumonia, or confirm normal findings. Processing happens asynchronously;
          you can continue using the app while the AI runs.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-6 bg-surface shadow-card cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 ${
            isDragActive ? "border-primary-500 bg-slate-900" : "border-slate-700"
          }`}
        >
          <input {...getInputProps()} aria-label="Upload chest X-ray image" />
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="h-12 w-12 rounded-full bg-slate-900 flex items-center justify-center">
              <FiUploadCloud className="h-6 w-6 text-primary-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-100">
                {isDragActive
                  ? "Drop the X-ray image here"
                  : "Drag and drop a chest X-ray, or click to browse"}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Accepted formats: JPG, JPEG, PNG — Max size: 10MB — Min resolution: 224x224
              </p>
            </div>
            {file && (
              <p className="mt-2 text-xs text-slate-300">
                Selected: <span className="font-semibold">{file.name}</span>{" "}
                <span className="text-slate-400">
                  ({formatFileSize(file.size)})
                </span>
              </p>
            )}
            {dimError && (
              <p className="mt-2 text-xs text-red-300" role="alert">
                {dimError}
              </p>
            )}
          </div>
        </div>

        {preview && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <figure className="bg-surface rounded-xl overflow-hidden border border-slate-800">
              <img
                src={preview}
                alt="Selected chest X-ray preview"
                className="w-full h-64 object-contain bg-black"
              />
              <figcaption className="px-4 py-2 text-xs text-slate-400">
                Preview of the uploaded image. Ensure it is a clear, properly
                centered chest X-ray.
              </figcaption>
            </figure>
            <div className="text-xs text-slate-400 space-y-2">
              <h2 className="text-sm font-semibold text-slate-100">
                Security & Privacy
              </h2>
              <ul className="list-disc list-inside space-y-1">
                <li>Images are validated server-side for type and size.</li>
                <li>Only anonymized X-rays should be uploaded.</li>
                <li>
                  This tool is for screening only and does not replace a medical
                  diagnosis.
                </li>
              </ul>
            </div>
          </div>
        )}

        <div className="flex items-center gap-3 mt-4">
          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-md hover:bg-primary-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-60 disabled:cursor-not-allowed"
            disabled={!file || isSubmitting || isPolling}
          >
            {isSubmitting || isPolling ? "Processing..." : "Analyze X-ray"}
          </button>
          {(isSubmitting || isPolling) && (
            <LoadingSpinner size="sm" label="Running AI analysis..." />
          )}
        </div>
      </form>
    </section>
  );
};

export default Upload;

