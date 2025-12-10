# app.py
import streamlit as st
import numpy as np
import pydicom
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Configuração do banco SQLite
engine = create_engine("sqlite:///dicom.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# Definição das tabelas
class Patient(Base):
    __tablename__ = "patient"
    patient_id = Column(String, primary_key=True)
    name = Column(String)
    sex = Column(String)
    birth_date = Column(String)
    studies = relationship("Study", back_populates="patient")

class Study(Base):
    __tablename__ = "study"
    study_uid = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("patient.patient_id"))
    description = Column(String)
    date = Column(String)
    patient = relationship("Patient", back_populates="studies")
    series = relationship("Series", back_populates="study")

class Series(Base):
    __tablename__ = "series"
    series_uid = Column(String, primary_key=True)
    study_uid = Column(String, ForeignKey("study.study_uid"))
    description = Column(String)
    modality = Column(String)
    study = relationship("Study", back_populates="series")
    images = relationship("Image", back_populates="series")

class Image(Base):
    __tablename__ = "image"
    sop_uid = Column(String, primary_key=True)
    series_uid = Column(String, ForeignKey("series.series_uid"))
    instance_number = Column(Integer)
    path = Column(String)
    series = relationship("Series", back_populates="images")

Base.metadata.create_all(engine)

# Função de window/level
def apply_wl(img, window, level):
    low, high = level - window/2, level + window/2
    img = np.clip(img, low, high)
    img = (img - low) / (high - low)
    return img

# Upload de arquivos
st.title("Mini PACS + Visualizador DICOM")
files = st.file_uploader("Selecione arquivos DICOM", type=["dcm"], accept_multiple_files=True)

if files:
    for f in files:
        ds = pydicom.dcmread(f, force=True)
        # Inserir paciente
        patient = session.get(Patient, ds.PatientID) or Patient(
            patient_id=ds.PatientID,
            name=str(getattr(ds, "PatientName", "")),
            sex=getattr(ds, "PatientSex", ""),
            birth_date=getattr(ds, "PatientBirthDate", "")
        )
        session.add(patient)

        # Inserir estudo
        study = session.get(Study, ds.StudyInstanceUID) or Study(
            study_uid=ds.StudyInstanceUID,
            patient=patient,
            description=getattr(ds, "StudyDescription", ""),
            date=getattr(ds, "StudyDate", "")
        )
        session.add(study)

        # Inserir série
        series = session.get(Series, ds.SeriesInstanceUID) or Series(
            series_uid=ds.SeriesInstanceUID,
            study=study,
            description=getattr(ds, "SeriesDescription", ""),
            modality=getattr(ds, "Modality", "")
        )
        session.add(series)

        # Inserir imagem
        image = Image(
            sop_uid=ds.SOPInstanceUID,
            series=series,
            instance_number=int(getattr(ds, "InstanceNumber", 0)),
            path=f.name
        )
        session.add(image)

    session.commit()
    st.success("Exames importados para o banco SQLite!")

# Browser de pacientes
patients = session.query(Patient).all()
for p in patients:
    with st.expander(f"Paciente: {p.name} ({p.patient_id})"):
        for s in p.studies:
            st.write(f"Estudo: {s.description} - {s.date}")
            for se in s.series:
                st.write(f"  Série: {se.description} ({se.modality})")
                if st.button(f"Visualizar série {se.series_uid}"):
                    # Carregar imagens da série
                    imgs = [pydicom.dcmread(img.path).pixel_array for img in se.images]
                    vol = np.stack(imgs, axis=0)

                    # Controles interativos
                    axis = st.selectbox("Plano", ["Axial (Z)", "Coronal (Y)", "Sagital (X)"])
                    window = st.slider("Window", 1, 4000, 400)
                    level = st.slider("Level", -1000, 1000, 40)

                    if axis.startswith("Axial"):
                        idx = st.slider("Corte axial (Z)", 0, vol.shape[0]-1, vol.shape[0]//2)
                        img = vol[idx,:,:]
                    elif axis.startswith("Coronal"):
                        idx = st.slider("Corte coronal (Y)", 0, vol.shape[1]-1, vol.shape[1]//2)
                        img = vol[:,idx,:]
                    else:
                        idx = st.slider("Corte sagital (X)", 0, vol.shape[2]-1, vol.shape[2]//2)
                        img = vol[:,:,idx]

                    img_wl = apply_wl(img, window, level)

                    fig, ax = plt.subplots()
                    ax.imshow(img_wl, cmap="gray")
                    ax.axis("off")
                    st.pyplot(fig)
