import { useState } from "react";
import PropTypes from "prop-types";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import { format } from "date-fns";

function ExportButton({ elementId, filename, data, type }) {
  const [exporting, setExporting] = useState(false);

  const exportToPDF = async () => {
    setExporting(true);
    try {
      const element = document.getElementById(elementId);
      if (!element) {
        throw new Error(`Element with id "${elementId}" not found`);
      }

      // Capture the element as canvas
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: "#ffffff",
      });

      // Create PDF
      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF({
        orientation: canvas.width > canvas.height ? "landscape" : "portrait",
        unit: "px",
        format: [canvas.width, canvas.height],
      });

      pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height);
      pdf.save(`${filename}.pdf`);
    } catch (error) {
      console.error("Failed to export PDF:", error);
      alert("Failed to export PDF. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const exportToCSV = () => {
    setExporting(true);
    try {
      if (!data || data.length === 0) {
        throw new Error("No data available to export");
      }

      // Convert data to CSV format
      const headers = Object.keys(data[0]);
      const csvContent = [
        headers.join(","),
        ...data.map((row) =>
          headers.map((header) => {
            const value = row[header];
            // Escape values containing commas or quotes
            if (typeof value === "string" && (value.includes(",") || value.includes('"'))) {
              return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
          }).join(",")
        ),
      ].join("\n");

      // Create blob and download
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", `${filename}.csv`);
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error("Failed to export CSV:", error);
      alert("Failed to export CSV. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const handleExport = () => {
    if (type === "pdf") {
      exportToPDF();
    } else if (type === "csv") {
      exportToCSV();
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={exporting}
      className="primary"
      style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
    >
      {exporting ? (
        <>
          <span>Exporting...</span>
        </>
      ) : (
        <>
          <span>Export {type.toUpperCase()}</span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </>
      )}
    </button>
  );
}

ExportButton.propTypes = {
  elementId: PropTypes.string,
  filename: PropTypes.string,
  data: PropTypes.array,
  type: PropTypes.oneOf(["pdf", "csv"]).isRequired,
};

ExportButton.defaultProps = {
  elementId: "analytics-content",
  filename: `analytics-export-${format(new Date(), "yyyy-MM-dd")}`,
  data: null,
};

export default ExportButton;
