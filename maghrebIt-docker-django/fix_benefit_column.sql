-- Fix benefit column in bondecommande table
-- This will change the benefit column to TEXT type to allow storing commission data

ALTER TABLE `bondecommande` MODIFY COLUMN `benefit` TEXT NULL;
