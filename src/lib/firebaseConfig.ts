// Firebase configuration for Invs Riego Comunitario
import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import { getAuth } from 'firebase/auth';
import { getStorage } from 'firebase/storage';

const firebaseConfig = {
  apiKey: "AIzaSyDcuRn_Eyci2HCd-Xo1bsd0YpHUeys-HaM",
  authDomain: "invs-riego-comunitario.firebaseapp.com",
  projectId: "invs-riego-comunitario",
  storageBucket: "invs-riego-comunitario.firebasestorage.app",
  messagingSenderId: "1052839638086",
  appId: "1:1052839638086:web:657b4ee041d16cd5b9c647"
};

const app = initializeApp(firebaseConfig);

export const db = getFirestore(app);
export const auth = getAuth(app);
export const storage = getStorage(app);
export default app;
