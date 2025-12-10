# app.py
import streamlit as st
import numpy as np
import pydicom
import matplotlib.pyplot as plt

st.title("Visualizador DICOM simples em Streamlit")

# Upload de múltiplos arquivos DICOM
files = st.file_uploader("Selecione arquivos DICOM da série", type=["dcm"], accept_multiple_files=True)

if files:
    # Ler todos os datasets
    datasets = [pydicom.dcmread(f, force=True) for f in files]

    # Ordenar pela posição da fatia (se disponível)
    def slice_position(ds):
        try:
            return float(ds.ImagePositionPatient[2])
        except Exception:
            return float(ds.InstanceNumber)
    datasets.sort(key=slice_position)

    # Montar volume numpy (Z, Y, X)
    slope = float(getattr(datasets[0], "RescaleSlope", 1.0))
    intercept = float(getattr(datasets[0], "RescaleIntercept", 0.0))
    vol = np.stack([ds.pixel_array.astype(np.float32) * slope + intercept for ds in datasets], axis=0)

    st.write(f"Volume carregado: {vol.shape}")

    # Controles
    axis = st.selectbox("Plano", ["Axial (Z)", "Coronal (Y)", "Sagital (X)"])
    index = st.slider("Índice da fatia", 0, vol.shape[0]-1, vol.shape[0]//2)
    window = st.slider("Window", 1, 4000, 400)
    level = st.slider("Level", -1000, 1000, 40)

    # Função de window/level
    def apply_wl(img, window, level):
        low, high = level - window/2, level + window/2
        img = np.clip(img, low, high)
        img = (img - low) / (high - low)
        return img

    # Selecionar fatia
    if axis.startswith("Axial"):
        img = vol[index,:,:]
    elif axis.startswith("Coronal"):
        img = vol[:,index,:]
    else:  # Sagital
        img = vol[:,:,index]

    img_wl = apply_wl(img, window, level)

    # Mostrar imagem
    fig, ax = plt.subplots()
    ax.imshow(img_wl, cmap="gray")
    ax.axis("off")
    st.pyplot(fig)

    # Projeções MIP/MinIP
    if st.checkbox("Mostrar projeção (MIP/MinIP)"):
        mode = st.selectbox("Modo", ["MIP", "MinIP"])
        if axis.startswith("Axial"):
            proj = vol.max(axis=0) if mode=="MIP" else vol.min(axis=0)
        elif axis.startswith("Coronal"):
            proj = vol.max(axis=1) if mode=="MIP" else vol.min(axis=1)
        else:
            proj = vol.max(axis=2) if mode=="MIP" else vol.min(axis=2)
        proj_wl = apply_wl(proj, window, level)
        fig2, ax2 = plt.subplots()
        ax2.imshow(proj_wl, cmap="gray")
        ax2.axis("off")
        st.pyplot(fig2)
