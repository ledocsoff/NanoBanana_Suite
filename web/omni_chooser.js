import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "omni.chooser",
    setup() {
        api.addEventListener("omni.chooser.display", (event) => {
            const data = event.detail;
            const nodeId = data.node_id;
            const images = data.images; // array of {filename, type, subfolder}
            const mode = data.mode;
            const timeout = data.timeout;
            
            // Create full screen overlay
            const overlay = document.createElement("div");
            overlay.style.position = "fixed";
            overlay.style.top = "0";
            overlay.style.left = "0";
            overlay.style.width = "100vw";
            overlay.style.height = "100vh";
            overlay.style.backgroundColor = "rgba(0,0,0,0.8)";
            overlay.style.zIndex = "9998";
            document.body.appendChild(overlay);

            // Create dialog box
            const dialog = document.createElement("div");
            dialog.style.position = "fixed";
            dialog.style.top = "50%";
            dialog.style.left = "50%";
            dialog.style.transform = "translate(-50%, -50%)";
            dialog.style.backgroundColor = "#2a2a2a";
            dialog.style.padding = "20px";
            dialog.style.zIndex = "9999";
            dialog.style.display = "flex";
            dialog.style.flexDirection = "column";
            dialog.style.gap = "15px";
            dialog.style.maxHeight = "90vh";
            dialog.style.maxWidth = "90vw";
            dialog.style.overflowY = "auto";
            dialog.style.borderRadius = "8px";
            dialog.style.boxShadow = "0 4px 15px rgba(0,0,0,0.5)";
            dialog.style.color = "#ffffff";
            dialog.style.fontFamily = "sans-serif";
            
            const header = document.createElement("div");
            header.style.display = "flex";
            header.style.justifyContent = "space-between";
            header.style.alignItems = "center";
            header.style.borderBottom = "1px solid #444";
            header.style.paddingBottom = "10px";

            const title = document.createElement("h2");
            title.textContent = "🎯 Sélection d'Image(s) - " + mode;
            title.style.margin = "0";
            title.style.fontSize = "1.5rem";
            header.appendChild(title);
            
            const timeoutDisplay = document.createElement("div");
            timeoutDisplay.style.fontSize = "1.2rem";
            timeoutDisplay.style.fontWeight = "bold";
            timeoutDisplay.style.color = "#ffdd57";
            header.appendChild(timeoutDisplay);
            
            dialog.appendChild(header);
            
            const imgContainer = document.createElement("div");
            imgContainer.style.display = "flex";
            imgContainer.style.flexWrap = "wrap";
            imgContainer.style.gap = "15px";
            imgContainer.style.justifyContent = "center";
            imgContainer.style.marginTop = "10px";
            
            let selectedIndices = new Set();
            
            images.forEach((img, idx) => {
                const imgWrapper = document.createElement("div");
                imgWrapper.style.position = "relative";
                imgWrapper.style.cursor = "pointer";
                
                const imgEl = document.createElement("img");
                const url = api.apiURL("/view?filename=" + encodeURIComponent(img.filename) + "&type=" + img.type + "&subfolder=" + img.subfolder);
                imgEl.src = url;
                imgEl.style.height = "300px";
                imgEl.style.objectFit = "contain";
                imgEl.style.border = "4px solid transparent";
                imgEl.style.borderRadius = "8px";
                imgEl.style.transition = "all 0.2s ease-in-out";
                
                const checkmark = document.createElement("div");
                checkmark.style.position = "absolute";
                checkmark.style.top = "10px";
                checkmark.style.right = "10px";
                checkmark.style.width = "30px";
                checkmark.style.height = "30px";
                checkmark.style.borderRadius = "50%";
                checkmark.style.backgroundColor = "#4CAF50";
                checkmark.style.color = "white";
                checkmark.style.display = "flex";
                checkmark.style.alignItems = "center";
                checkmark.style.justifyContent = "center";
                checkmark.style.fontWeight = "bold";
                checkmark.style.fontSize = "18px";
                checkmark.style.opacity = "0";
                checkmark.style.transition = "opacity 0.2s";
                checkmark.innerHTML = "✓";
                
                imgWrapper.appendChild(imgEl);
                imgWrapper.appendChild(checkmark);
                
                const updateSelectionUI = () => {
                    if (selectedIndices.has(idx)) {
                        imgEl.style.borderColor = "#4CAF50";
                        imgEl.style.transform = "scale(0.98)";
                        checkmark.style.opacity = "1";
                    } else {
                        imgEl.style.borderColor = "transparent";
                        imgEl.style.transform = "scale(1)";
                        checkmark.style.opacity = "0";
                    }
                };
                
                imgWrapper.onclick = () => {
                    if (mode === "Sélection unique") {
                        selectedIndices.clear();
                        Array.from(imgContainer.children).forEach((child, i) => {
                            child.querySelector("img").style.borderColor = "transparent";
                            child.querySelector("img").style.transform = "scale(1)";
                            child.querySelector("div").style.opacity = "0";
                        });
                        selectedIndices.add(idx);
                        updateSelectionUI();
                    } else {
                        if (selectedIndices.has(idx)) {
                            selectedIndices.delete(idx);
                        } else {
                            selectedIndices.add(idx);
                        }
                        updateSelectionUI();
                    }
                };
                
                imgContainer.appendChild(imgWrapper);
            });
            dialog.appendChild(imgContainer);
            
            const submitBtn = document.createElement("button");
            submitBtn.textContent = "Confirmer la sélection";
            submitBtn.style.padding = "15px 20px";
            submitBtn.style.backgroundColor = "#4CAF50";
            submitBtn.style.color = "white";
            submitBtn.style.border = "none";
            submitBtn.style.cursor = "pointer";
            submitBtn.style.borderRadius = "6px";
            submitBtn.style.fontSize = "1.2rem";
            submitBtn.style.fontWeight = "bold";
            submitBtn.style.marginTop = "20px";
            submitBtn.style.alignSelf = "center";
            submitBtn.style.transition = "background-color 0.2s";
            
            submitBtn.onmouseover = () => submitBtn.style.backgroundColor = "#45a049";
            submitBtn.onmouseout = () => submitBtn.style.backgroundColor = "#4CAF50";
            
            let timeLeft = timeout;
            let timer = setInterval(() => {
                timeLeft--;
                timeoutDisplay.textContent = "⏳ " + timeLeft + "s";
                if (timeLeft <= 0) {
                    clearInterval(timer);
                    closeDialog();
                }
            }, 1000);
            
            const closeDialog = () => {
                document.body.removeChild(dialog);
                document.body.removeChild(overlay);
            };
            
            submitBtn.onclick = async () => {
                if (selectedIndices.size === 0 && mode === "Sélection unique") {
                    alert("⚠️ Veuillez sélectionner au moins une image.");
                    return;
                }
                
                submitBtn.disabled = true;
                submitBtn.textContent = "Envoi...";
                submitBtn.style.backgroundColor = "#888";
                clearInterval(timer);
                
                try {
                    await fetch("/omni/chooser/select", {
                        method: "POST",
                        body: JSON.stringify({
                            node_id: nodeId,
                            indices: Array.from(selectedIndices)
                        }),
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                } catch(e) {
                    console.error("[Omni] Error sending selection", e);
                }
                
                closeDialog();
            };
            
            dialog.appendChild(submitBtn);
            document.body.appendChild(dialog);
        });
    }
});
