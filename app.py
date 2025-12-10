# app.py
import streamlit as st
import os
import numpy as np
import pydicom
import vtk
import vtk.util.numpy_support as ns
from dicom_io import load_series
from volume_tools import numpy_to_vtk_image, reslice_mpr, slab_reslice

st.title("Visualizador DICOM - MPR/MIP em Streamlit")

# Upload de pasta (zip) ou arquivos
uploaded_files = st.file_uploader("Selecione arquivos DICOM", type=["dcm"], accept_multiple_files=True)

if uploaded_files:
    # Salvar temporariamente
    import tempfile
    tmpdir = tempfile.mkdtemp()
    for f in uploaded_files:
        with open(os.path.join(tmpdir, f.name), "wb") as out:
            out.write(f.getbuffer())

    vol, spacing, meta = load_series(tmpdir)
    st.write(f"Volume carregado: {vol.shape}, Spacing: {spacing}")

    # Controles
    window = st.slider("Window", 1, 4000, 400)
    level = st.slider("Level", -1000, 1000, 40)
    slab = st.slider("Espessura slab (mm)", 0, 100, 20)
    mode = st.selectbox("Modo projeção", ["MIP", "MinIP", "Mean"])

    # Converter para VTK
    image_data = numpy_to_vtk_image(vol, spacing)

    # Axial MPR
    axial_matrix = vtk.vtkMatrix4x4()
    axial_matrix.Identity()
    axial_reslice = reslice_mpr(image_data, axial_matrix)
    axial_img = axial_reslice.GetOutput()

    # Slab MIP/MinIP
    slab_res = slab_reslice(image_data, axial_matrix, thickness_mm=slab, mode=mode.lower())
    slab_img = slab_res.GetOutput()

    # Converter para numpy para exibir no Streamlit
    def vtk_to_numpy_img(vtk_img):
        arr = ns.vtk_to_numpy(vtk_img.GetPointData().GetScalars())
        dims = vtk_img.GetDimensions()
        return arr.reshape(dims[2], dims[1], dims[0])

    axial_np = vtk_to_numpy_img(axial_img)
    slab_np = vtk_to_numpy_img(slab_img)

    st.image(axial_np[axial_np.shape[0]//2,:,:], caption="Axial MPR", clamp=True)
    st.image(slab_np[slab_np.shape[0]//2,:,:], caption=f"{mode} projeção", clamp=True)
