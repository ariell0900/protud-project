--
-- PostgreSQL database dump
--

\restrict t0Q7noSLucqkuAKjVBpTjDf9mMGX02xtfCIeeCfLMGlDbNNq6PQV4IR9DsspDLs

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alertas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alertas (
    id integer NOT NULL,
    robot_id integer,
    tipo character varying(50),
    descripcion text,
    foto_url character varying(255),
    fecha_hora timestamp without time zone DEFAULT now(),
    atendida boolean DEFAULT false
);


--
-- Name: alertas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alertas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: alertas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alertas_id_seq OWNED BY public.alertas.id;


--
-- Name: imagenes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.imagenes (
    id integer NOT NULL,
    alerta_id integer,
    imagen_url text NOT NULL,
    fecha_captura timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: imagenes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.imagenes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: imagenes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.imagenes_id_seq OWNED BY public.imagenes.id;


--
-- Name: notificaciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notificaciones (
    id integer NOT NULL,
    alerta_id integer,
    mensaje text NOT NULL,
    fecha_envio timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    leida boolean DEFAULT false,
    estado_envio character varying(20) DEFAULT 'pendiente'::character varying NOT NULL,
    CONSTRAINT notificaciones_estado_envio_check CHECK (((estado_envio)::text = ANY ((ARRAY['pendiente'::character varying, 'enviada'::character varying, 'fallida'::character varying])::text[])))
);


--
-- Name: notificaciones_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notificaciones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notificaciones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notificaciones_id_seq OWNED BY public.notificaciones.id;


--
-- Name: robots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.robots (
    id integer NOT NULL,
    nombre character varying(100),
    ubicacion character varying(150),
    estado character varying(30),
    fecha_registro timestamp without time zone DEFAULT now(),
    CONSTRAINT robots_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'inactivo'::character varying, 'desconectado'::character varying])::text[])))
);


--
-- Name: robots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.robots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: robots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.robots_id_seq OWNED BY public.robots.id;


--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuarios (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    email character varying(150) NOT NULL,
    password_hash character varying(255),
    rol character varying(20) NOT NULL,
    activo boolean DEFAULT true,
    fecha_registro timestamp without time zone DEFAULT now(),
    CONSTRAINT usuarios_rol_check CHECK (((rol)::text = ANY ((ARRAY['administrador'::character varying, 'operador'::character varying])::text[])))
);


--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuarios_id_seq OWNED BY public.usuarios.id;


--
-- Name: alertas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alertas ALTER COLUMN id SET DEFAULT nextval('public.alertas_id_seq'::regclass);


--
-- Name: imagenes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.imagenes ALTER COLUMN id SET DEFAULT nextval('public.imagenes_id_seq'::regclass);


--
-- Name: notificaciones id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificaciones ALTER COLUMN id SET DEFAULT nextval('public.notificaciones_id_seq'::regclass);


--
-- Name: robots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.robots ALTER COLUMN id SET DEFAULT nextval('public.robots_id_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios ALTER COLUMN id SET DEFAULT nextval('public.usuarios_id_seq'::regclass);


--
-- Name: alertas alertas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alertas
    ADD CONSTRAINT alertas_pkey PRIMARY KEY (id);


--
-- Name: imagenes imagenes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.imagenes
    ADD CONSTRAINT imagenes_pkey PRIMARY KEY (id);


--
-- Name: notificaciones notificaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificaciones
    ADD CONSTRAINT notificaciones_pkey PRIMARY KEY (id);


--
-- Name: robots robots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.robots
    ADD CONSTRAINT robots_pkey PRIMARY KEY (id);


--
-- Name: usuarios usuarios_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_email_key UNIQUE (email);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: alertas alertas_robot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alertas
    ADD CONSTRAINT alertas_robot_id_fkey FOREIGN KEY (robot_id) REFERENCES public.robots(id);


--
-- Name: imagenes imagenes_alerta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.imagenes
    ADD CONSTRAINT imagenes_alerta_id_fkey FOREIGN KEY (alerta_id) REFERENCES public.alertas(id);


--
-- Name: notificaciones notificaciones_alerta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificaciones
    ADD CONSTRAINT notificaciones_alerta_id_fkey FOREIGN KEY (alerta_id) REFERENCES public.alertas(id);


--
-- PostgreSQL database dump complete
--

\unrestrict t0Q7noSLucqkuAKjVBpTjDf9mMGX02xtfCIeeCfLMGlDbNNq6PQV4IR9DsspDLs

